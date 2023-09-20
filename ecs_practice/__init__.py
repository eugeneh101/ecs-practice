# aws_cdk does not have native way to push container image to ECR
# (other than `container-assets` ECR repo), so have to use `cdk_ecr_deployment`
import cdk_ecr_deployment as ecr_deploy
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_sqs as sqs,
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
            role_name="ecs-practice-iam-role",  # hard coded
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),  ### later principle of least privileges
            ],
        )

        self.dynamodb_table = dynamodb.Table(
            self,
            "DynamodbTable",
            table_name="ecs-practice-table",  # hard coded
            partition_key=dynamodb.Attribute(
                name="type", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="datetime", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.sqs_queue = sqs.Queue(
            self,
            "SqsQueue",
            queue_name="ecs-practice-queue",  # hard coded
            removal_policy=RemovalPolicy.DESTROY,
            # dead_letter_queue=None,
        )

        self.vpc = ec2.Vpc(
            self,
            "VPC",
            vpc_name="ecs-practice-vpc",  # hard coded
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public-Subnet",  # so don't have to use VPC gateway (DynamoDB) + interface (SQS) endpoints
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
            availability_zones=[
                f"{environment['AWS_REGION']}{az}"
                for az in environment["AVAILABILITY_ZONES"]
            ],
        )
        # self.vpc.add_s3_endpoint("S3Endpoint")
        # self.vpc.add_interface_endpoint("EcrDockerEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER)
        # self.vpc.add_interface_endpoint("EcrEndpoint", service=ec2.InterfaceVpcEndpointAwsService.ECR)
        # self.vpc.add_interface_endpoint("CloudWatchLogsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS)

        self.ecr_repo = ecr.Repository(
            self,
            "EcrRepo",
            repository_name="ecs-practice-ecr-repo",  # hard coded
            auto_delete_images=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.ecs_cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name="ecs-practice-cluster",  # hard coded
            vpc=self.vpc,
        )

        asset = ecr_assets.DockerImageAsset(
            self, "EcrImage", directory="service"
        )  # uploads to `container-assets` ECR repo
        image = ecs.ContainerImage.from_docker_image_asset(asset=asset)
        # image = ecs.ContainerImage.from_registry("springio/gs-spring-boot-docker")

        # connecting AWS resources together
        self.ecs_task_definition = ecs.TaskDefinition(
            self,
            "EcsTaskDefinition",
            family="ecs-practice-task-definition",  # hard coded
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
        container = self.ecs_task_definition.add_container(
            "ecs-practice-container", image=image
        )
        # container.add_port_mappings(ecs.PortMapping(container_port=8080))
        ecr_deploy.ECRDeployment(  # upload to desired ECR repo
            self,
            "PushEcrImage",
            src=ecr_deploy.DockerImageName(asset.image_uri),
            dest=ecr_deploy.DockerImageName(self.ecr_repo.repository_uri),
        )
        self.dynamodb_table.grant_write_data(self.role)
        self.sqs_queue.grant_consume_messages(self.role)
