#!/usr/bin/env python3
import aws_cdk as cdk
from integra_stack import IntegraStack

app = cdk.App()
IntegraStack(app, "IntegraStack")
app.synth()
