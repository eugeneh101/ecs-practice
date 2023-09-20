import aws_cdk as cdk

from ecs_practice import EcsPracticeStack


app = cdk.App()
environment = app.node.try_get_context("environment")
EcsPracticeStack(
    app,
    "EcsPracticeStack",
    env=cdk.Environment(region=environment["AWS_REGION"]),    
    environment=environment,
)
app.synth()
