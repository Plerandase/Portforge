# DR VPC Configuration
# CIDR: 10.20.0.0/16 (Primary: 10.10.0.0/16)

resource "aws_vpc" "dr_vpc" {
  provider             = aws.dr
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "dr_igw" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr_vpc.id

  tags = { Name = "${var.project_name}-igw" }
}

# Public Subnets
resource "aws_subnet" "dr_pub_sub1" {
  provider                = aws.dr
  vpc_id                  = aws_vpc.dr_vpc.id
  cidr_block              = var.public_subnet_cidrs[0]
  availability_zone       = var.availability_zones[0]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-pub-sub1" }
}

resource "aws_subnet" "dr_pub_sub2" {
  provider                = aws.dr
  vpc_id                  = aws_vpc.dr_vpc.id
  cidr_block              = var.public_subnet_cidrs[1]
  availability_zone       = var.availability_zones[1]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-pub-sub2" }
}

# Private Subnets (EKS Nodes)
resource "aws_subnet" "dr_pri_sub1" {
  provider          = aws.dr
  vpc_id            = aws_vpc.dr_vpc.id
  cidr_block        = var.private_subnet_cidrs[0]
  availability_zone = var.availability_zones[0]

  tags = { Name = "${var.project_name}-pri-sub1" }
}

resource "aws_subnet" "dr_pri_sub2" {
  provider          = aws.dr
  vpc_id            = aws_vpc.dr_vpc.id
  cidr_block        = var.private_subnet_cidrs[1]
  availability_zone = var.availability_zones[1]

  tags = { Name = "${var.project_name}-pri-sub2" }
}

# DB Subnets
resource "aws_subnet" "dr_db_sub1" {
  provider          = aws.dr
  vpc_id            = aws_vpc.dr_vpc.id
  cidr_block        = var.db_subnet_cidrs[0]
  availability_zone = var.availability_zones[0]

  tags = { Name = "${var.project_name}-db-sub1" }
}

resource "aws_subnet" "dr_db_sub2" {
  provider          = aws.dr
  vpc_id            = aws_vpc.dr_vpc.id
  cidr_block        = var.db_subnet_cidrs[1]
  availability_zone = var.availability_zones[1]

  tags = { Name = "${var.project_name}-db-sub2" }
}

# NAT Gateways
resource "aws_eip" "dr_nat_eip1" {
  provider = aws.dr
  domain   = "vpc"

  tags = { Name = "${var.project_name}-nat-eip1" }
}

resource "aws_eip" "dr_nat_eip2" {
  provider = aws.dr
  domain   = "vpc"

  tags = { Name = "${var.project_name}-nat-eip2" }
}

resource "aws_nat_gateway" "dr_natgw1" {
  provider      = aws.dr
  allocation_id = aws_eip.dr_nat_eip1.id
  subnet_id     = aws_subnet.dr_pub_sub1.id

  tags       = { Name = "${var.project_name}-natgw1" }
  depends_on = [aws_internet_gateway.dr_igw]
}

resource "aws_nat_gateway" "dr_natgw2" {
  provider      = aws.dr
  allocation_id = aws_eip.dr_nat_eip2.id
  subnet_id     = aws_subnet.dr_pub_sub2.id

  tags       = { Name = "${var.project_name}-natgw2" }
  depends_on = [aws_internet_gateway.dr_igw]
}

# Route Tables
resource "aws_route_table" "dr_pub_rt" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dr_igw.id
  }

  tags = { Name = "${var.project_name}-pub-rt" }
}

resource "aws_route_table" "dr_pri_rt1" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.dr_natgw1.id
  }

  tags = { Name = "${var.project_name}-pri-rt1" }
}

resource "aws_route_table" "dr_pri_rt2" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.dr_natgw2.id
  }

  tags = { Name = "${var.project_name}-pri-rt2" }
}

resource "aws_route_table" "dr_db_rt" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr_vpc.id

  tags = { Name = "${var.project_name}-db-rt" }
}

# Route Table Associations
resource "aws_route_table_association" "dr_pub1_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_pub_sub1.id
  route_table_id = aws_route_table.dr_pub_rt.id
}

resource "aws_route_table_association" "dr_pub2_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_pub_sub2.id
  route_table_id = aws_route_table.dr_pub_rt.id
}

resource "aws_route_table_association" "dr_pri1_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_pri_sub1.id
  route_table_id = aws_route_table.dr_pri_rt1.id
}

resource "aws_route_table_association" "dr_pri2_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_pri_sub2.id
  route_table_id = aws_route_table.dr_pri_rt2.id
}

resource "aws_route_table_association" "dr_db1_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_db_sub1.id
  route_table_id = aws_route_table.dr_db_rt.id
}

resource "aws_route_table_association" "dr_db2_rt_asso" {
  provider       = aws.dr
  subnet_id      = aws_subnet.dr_db_sub2.id
  route_table_id = aws_route_table.dr_db_rt.id
}

# Security Groups
resource "aws_security_group" "dr_pub_sg" {
  provider    = aws.dr
  name        = "${var.project_name}-pub-sg"
  description = "Public security group for ALB"
  vpc_id      = aws_vpc.dr_vpc.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-pub-sg" }
}
