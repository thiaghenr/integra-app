"""
Integra - VPC unica com ECS Fargate (dev + prod) sem ALB nem NAT gateway,
RDS PostgreSQL isolado em subnet privada, TLS via sidecar Caddy.

Mesma arquitetura do template.yaml (CloudFormation) -- aqui em CDK a parte
dev/prod vira um metodo Python chamado duas vezes, em vez de blocos YAML
duplicados.
"""

from dataclasses import dataclass

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecr as ecr,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

# TODO ajuste antes do primeiro deploy:
# - GITHUB_REPO: "owner/repo" exato deste repositorio no GitHub (usado pra
#   restringir quem pode assumir a role de deploy via OIDC)
# - HOSTED_ZONE_ID: id do hosted zone Route 53 ja existente (ex.: Z0123456789ABCDEFGHI)
GITHUB_REPO = "thiaghenr/integra-app"
HOSTED_ZONE_ID = "Z00658691ZOQWYAUAOIMY"


@dataclass
class EnvConfig:
    name: str
    domain: str
    desired_count: int
    cpu: int
    memory: int


class IntegraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---------- Rede ----------
        # nat_gateways=0 e subnets isoladas (sem rota de internet) e o que
        # substitui o par NAT gateway + subnet privada "com egress" que o
        # CDK cria por padrao. ECS fica na subnet publica com IP proprio.
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="private-isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        self.ecs_sg = ec2.SecurityGroup(
            self,
            "EcsSecurityGroup",
            vpc=self.vpc,
            description="ECS tasks - so 80 (desafio ACME) e 443 (app) de entrada",
        )
        self.ecs_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        self.ecs_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))

        self.rds_sg = ec2.SecurityGroup(
            self,
            "RdsSecurityGroup",
            vpc=self.vpc,
            description="RDS - so aceita conexao das tasks do ECS",
        )
        self.rds_sg.add_ingress_rule(self.ecs_sg, ec2.Port.tcp(5432))

        # ---------- ECR (compartilhado entre dev e prod) ----------
        self.repository = ecr.Repository(
            self,
            "Repository",
            repository_name="integra-app",
            image_scan_on_push=True,
        )

        # ---------- ECS cluster (compartilhado) ----------
        self.cluster = ecs.Cluster(self, "Cluster", vpc=self.vpc, cluster_name="integra-cluster")

        # Somente dev ativo por enquanto. Prod comentado ate ser reativado --
        # reaproveita o mesmo metodo, so descomentar quando for a hora.
        self._build_environment(
            EnvConfig(name="dev", domain="dev.projetosei.com.br", desired_count=1, cpu=256, memory=512)
        )
        # self._build_environment(
        #     EnvConfig(name="prod", domain="projetosei.com.br", desired_count=2, cpu=512, memory=1024)
        # )

        self._build_github_deploy_role()

    def _build_github_deploy_role(self) -> None:
        # Role assumida via OIDC pelo GitHub Actions -- sem access key de
        # longa duracao guardada em secret nenhum. Escopo: so este repo, so
        # a branch main (cobre tanto "push em main" quanto workflow_dispatch
        # disparado a partir da main).
        #
        # Se a conta AWS ja tiver um provider OIDC do GitHub (de outro
        # projeto), troque as duas linhas abaixo por:
        #   github_oidc_provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
        #       self, "GithubOidcProvider", "arn:aws:iam::<account>:oidc-provider/token.actions.githubusercontent.com"
        #   )
        github_oidc_provider = iam.OpenIdConnectProvider(
            self,
            "GithubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        github_deploy_role = iam.Role(
            self,
            "GithubDeployRole",
            role_name="integra-github-deploy",
            max_session_duration=Duration.hours(1),
            assumed_by=iam.WebIdentityPrincipal(
                github_oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        # O job no deploy.yml declara "environment: dev/staging/prod", o que muda o
                        # formato do "sub" do token OIDC de "repo:OWNER/REPO:ref:refs/heads/BRANCH"
                        # para "repo:OWNER/REPO:environment:NOME" (ver docs do GitHub sobre OIDC).
                        # Aceita os dois formatos -- environment (o que de fato acontece hoje) e
                        # ref/main (caso algum job futuro rode sem "environment:").
                        "token.actions.githubusercontent.com:sub": [
                            f"repo:{GITHUB_REPO}:ref:refs/heads/main",
                            f"repo:{GITHUB_REPO}:environment:*",
                        ],
                    },
                },
            ),
        )

        # Escopo deliberadamente no nivel do repo ECR / cluster ECS (nao por
        # service/task especifico) -- assim reativar o prod mais pra frente
        # nao exige mexer nessa role de novo.
        self.repository.grant_pull_push(github_deploy_role)

        github_deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:UpdateService",
                    "ecs:DescribeServices",
                    "ecs:DescribeTasks",
                    "ecs:ListTasks",
                ],
                resources=[
                    self.cluster.cluster_arn,
                    f"arn:aws:ecs:{self.region}:{self.account}:service/{self.cluster.cluster_name}/*",
                    f"arn:aws:ecs:{self.region}:{self.account}:task/{self.cluster.cluster_name}/*",
                ],
            )
        )

        # DescribeNetworkInterfaces nao suporta escopo por recurso -- e uma
        # acao somente leitura, risco baixo com Resource: "*".
        github_deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ec2:DescribeNetworkInterfaces"],
                resources=["*"],
            )
        )

        github_deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["route53:ChangeResourceRecordSets", "route53:GetHostedZone"],
                resources=[f"arn:aws:route53:::hostedzone/{HOSTED_ZONE_ID}"],
            )
        )

        CfnOutput(self, "GithubDeployRoleArn", value=github_deploy_role.role_arn)

    def _build_environment(self, cfg: EnvConfig) -> None:
        prefix = cfg.name.capitalize()

        # SECRET_KEY / CHATBOT_API_KEY do ambiente -- gerado, nunca em texto plano
        app_secret = secretsmanager.Secret(
            self,
            f"{prefix}AppSecrets",
            secret_name=f"integra/{cfg.name}/app-secrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template="{}",
                generate_string_key="SECRET_KEY",
                exclude_punctuation=True,
                password_length=48,
            ),
        )

        # RDS single-AZ, subnet isolada, sem IP publico. from_generated_secret
        # cria e gerencia o secret de username/password automaticamente.
        database = rds.DatabaseInstance(
            self,
            f"{prefix}Database",
            # .of(...) evita depender de uma constante fixa da lib que pode
            # ficar desatualizada -- confira a minor mais recente em
            # aws rds describe-db-engine-versions --engine postgres antes do deploy
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.of("16.14", "16")),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.rds_sg],
            credentials=rds.Credentials.from_generated_secret("integra"),
            database_name="integra_db",
            allocated_storage=20,
            storage_encrypted=True,
            multi_az=False,
            publicly_accessible=False,
            backup_retention=Duration.days(7),
            removal_policy=RemovalPolicy.SNAPSHOT,
        )

        log_group = logs.LogGroup(
            self,
            f"{prefix}LogGroup",
            log_group_name=f"/ecs/integra-{cfg.name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            f"{prefix}TaskDefinition",
            family=f"integra-{cfg.name}",
            cpu=cfg.cpu,
            memory_limit_mib=cfg.memory,
        )

        # NOTA (igual no template CFN): o secret do RDS so tem username/password.
        # host/port/dbname vao como env var normal (nao sao segredo). O
        # entrypoint.sh do app precisa montar a DATABASE_URL a partir de
        # POSTGRES_USER/PASSWORD/HOST/PORT/DB antes de subir o uvicorn.
        app_container = task_definition.add_container(
            "app",
            image=ecs.ContainerImage.from_ecr_repository(self.repository, cfg.name + "-latest"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="app", log_group=log_group),
            environment={
                "ENV": cfg.name,
                "POSTGRES_HOST": database.db_instance_endpoint_address,
                "POSTGRES_PORT": database.db_instance_endpoint_port,
                "POSTGRES_DB": "integra_db",
            },
            secrets={
                "SECRET_KEY": ecs.Secret.from_secrets_manager(app_secret, "SECRET_KEY"),
                "POSTGRES_USER": ecs.Secret.from_secrets_manager(database.secret, "username"),
                "POSTGRES_PASSWORD": ecs.Secret.from_secrets_manager(database.secret, "password"),
            },
        )
        app_container.add_port_mappings(ecs.PortMapping(container_port=8000))

        caddy_container = task_definition.add_container(
            "caddy",
            image=ecs.ContainerImage.from_registry("caddy:2-alpine"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="caddy", log_group=log_group),
            command=["caddy", "reverse-proxy", "--from", f"https://{cfg.domain}", "--to", "localhost:8000"],
        )
        caddy_container.add_port_mappings(
            ecs.PortMapping(container_port=443),
            ecs.PortMapping(container_port=80),
        )

        ecs.FargateService(
            self,
            f"{prefix}Service",
            cluster=self.cluster,
            service_name=f"integra-{cfg.name}",
            task_definition=task_definition,
            desired_count=cfg.desired_count,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            assign_public_ip=True,
            security_groups=[self.ecs_sg],
        )

        # grant_read faz o mesmo que a Policy inline no CFN, so que sem
        # escrever o ARN na mao
        app_secret.grant_read(task_definition.execution_role)
        # database.secret e tipado como ISecret | None pela lib do CDK (so e
        # None se as credenciais nao vierem do Secrets Manager) -- aqui
        # sempre vem, via Credentials.from_generated_secret() acima.
        assert database.secret is not None
        database.secret.grant_read(task_definition.execution_role)
