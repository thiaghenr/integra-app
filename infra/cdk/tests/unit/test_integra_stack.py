"""
Testes de asserção da stack CDK -- travam no CI as decisões de arquitetura
que já discutimos (sem ALB, sem NAT gateway, só dev ativo por enquanto),
pra ninguém reintroduzir esse custo sem perceber num PR futuro.
"""

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template
from integra_stack import IntegraStack


def _template() -> Template:
    app = cdk.App()
    stack = IntegraStack(app, "TestStack")
    return Template.from_stack(stack)


def test_no_nat_gateway():
    # O motivo de existir esse desenho: NAT gateway era ~$37/mes por ambiente.
    _template().resource_count_is("AWS::EC2::NatGateway", 0)


def test_no_load_balancer():
    # ALB era ~$32/mes por ambiente -- substituido por IP publico + Caddy.
    _template().resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 0)


def test_only_dev_environment_active():
    # Prod fica comentado em _build_environment ate ser reativado.
    template = _template()
    template.resource_count_is("AWS::ECS::Service", 1)
    template.resource_count_is("AWS::ECS::TaskDefinition", 1)
    template.resource_count_is("AWS::RDS::DBInstance", 1)


def test_rds_is_not_publicly_accessible_and_single_az():
    _template().has_resource_properties(
        "AWS::RDS::DBInstance",
        {
            "PubliclyAccessible": False,
            "MultiAZ": False,
        },
    )


def test_ecs_service_runs_in_public_subnet_with_own_ip():
    # Sem ALB na frente, a task precisa do proprio IP publico pra ser alcancada
    # (e pro Caddy sidecar conseguir o desafio ACME na porta 80).
    _template().has_resource_properties(
        "AWS::ECS::Service",
        {
            "LaunchType": "FARGATE",
            "NetworkConfiguration": {
                "AwsvpcConfiguration": {
                    "AssignPublicIp": "ENABLED",
                }
            },
        },
    )


def test_ecs_task_has_app_and_caddy_containers():
    template = _template()
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": Match.array_with(
                [
                    Match.object_like({"Name": "app"}),
                    Match.object_like({"Name": "caddy"}),
                ]
            )
        },
    )


def test_db_credentials_are_not_hardcoded():
    # username/password do banco tem que vir de Secrets Manager, nunca em
    # texto plano na task definition.
    template = _template()
    containers = template.find_resources("AWS::ECS::TaskDefinition")
    for resource in containers.values():
        for container in resource["Properties"]["ContainerDefinitions"]:
            if container["Name"] != "app":
                continue
            secret_names = {s["Name"] for s in container.get("Secrets", [])}
            assert "POSTGRES_PASSWORD" in secret_names
            env_names = {e["Name"] for e in container.get("Environment", [])}
            assert "POSTGRES_PASSWORD" not in env_names


def test_github_deploy_role_has_no_long_lived_credentials():
    # Nada de IAM User / AccessKey pro GitHub Actions -- so a role assumida
    # via OIDC. Se alguem trocar isso por uma access key fixa, o teste falha.
    template = _template()
    template.resource_count_is("AWS::IAM::User", 0)
    template.resource_count_is("AWS::IAM::AccessKey", 0)


def test_github_deploy_role_is_scoped_to_this_repo_and_main_branch():
    # A condicao StringLike do "sub" nao pode ser um wildcard solto tipo
    # "repo:*" -- tem que apontar pro repo especifico, senao qualquer
    # workflow de qualquer repo do GitHub poderia assumir essa role.
    #
    # Aceita duas formas do "sub", porque o deploy.yml declara "environment:"
    # nos jobs -- isso muda o token OIDC do GitHub de
    # "repo:OWNER/REPO:ref:refs/heads/BRANCH" para
    # "repo:OWNER/REPO:environment:NOME". Ver docs do GitHub sobre OIDC.
    template = _template()
    roles = template.find_resources(
        "AWS::IAM::Role",
        {"Properties": {"RoleName": "integra-github-deploy"}},
    )
    assert len(roles) == 1
    role = next(iter(roles.values()))
    statement = role["Properties"]["AssumeRolePolicyDocument"]["Statement"][0]
    sub_conditions = statement["Condition"]["StringLike"]["token.actions.githubusercontent.com:sub"]
    assert isinstance(sub_conditions, list)
    for sub_condition in sub_conditions:
        assert sub_condition.startswith("repo:")
        assert sub_condition != "repo:*"
    assert any(":ref:refs/heads/main" in c for c in sub_conditions)
    assert any(":environment:" in c for c in sub_conditions)
