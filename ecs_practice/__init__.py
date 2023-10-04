# aws_cdk does not have native way to push container image to ECR
# (other than `container-assets` ECR repo), so have to use `cdk_ecr_deployment`
import cdk_ecr_deployment as ecr_deploy
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class EcsPracticeStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, environment: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.role = iam.Role(
            self,
            "EcsTaskExecutionRole",
            role_name=environment["IAM_ROLE_NAME"],
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),  ### later principle of least privileges
            ],
        )

        self.vpc = ec2.Vpc(
            self,
            "VPC",
            vpc_name=environment["VPC_NAME"],
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public-Subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
            ],
            availability_zones=[
                f"{environment['AWS_REGION']}{az}"
                for az in environment["AVAILABILITY_ZONES"]
            ],
        )
        self.security_group_allow_port_80 = ec2.SecurityGroup(
            self,
            "SecurityGroupPortAllowPort80",
            vpc=self.vpc,
            security_group_name="allow-port-80",
            allow_all_outbound=True,
        )
        self.security_group_allow_port_80.add_ingress_rule(  # for FastAPI
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )

        self.ecr_repo = ecr.Repository(
            self,
            "EcrRepo",
            repository_name=environment["ECR_REPO_NAME"],
            auto_delete_images=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.ecs_cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=environment["ECS_CLUSTER_NAME"],
            vpc=self.vpc,
        )

        asset = ecr_assets.DockerImageAsset(
            self, "EcrImage", directory="service"
        )  # uploads to `container-assets` ECR repo

        # connecting AWS resources together
        ecr_deploy.ECRDeployment(  # upload to desired ECR repo
            self,
            "PushEcrImage",
            src=ecr_deploy.DockerImageName(asset.image_uri),
            dest=ecr_deploy.DockerImageName(self.ecr_repo.repository_uri),
        )
        image = ecs.ContainerImage.from_ecr_repository(repository=self.ecr_repo)

        self.ecs_task_definition = ecs.TaskDefinition(
            self,
            "EcsTaskDefinition",
            family=environment["ECS_TASK_DEFINITION_NAME"],
            compatibility=ecs.Compatibility.FARGATE,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.X86_64,
            ),
            cpu="256",  # 0.25 CPU
            memory_mib="512",  # 0.5 GB RAM
            # ephemeral_storage_gib=None,
            # volumes=None
            execution_role=self.role,
            task_role=self.role,
        )
        log_group = logs.LogGroup(
            self,
            "TaskDefinitionLogGroup",
            log_group_name=f"/ecs/{environment['ECS_TASK_DEFINITION_NAME']}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        container = self.ecs_task_definition.add_container(
            "ecs-practice-container",
            image=image,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=log_group,
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
        )
        container.add_port_mappings(ecs.PortMapping(host_port=80, container_port=80))
