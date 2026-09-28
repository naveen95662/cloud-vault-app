# 1. DB Subnet Group (Binds 2 Private DB Subnets across AZs)
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${var.environment}-rds-subnet-group"
  subnet_ids = [aws_subnet.private_db_1.id, aws_subnet.private_db_2.id]

  tags = {
    Name = "${var.environment}-rds-subnet-group"
  }
}

# 2. Amazon RDS MySQL Instance (Single-AZ for Free Tier compliance)
resource "aws_db_instance" "rds" {
  identifier             = "${var.environment}-mysql-db"
  allocated_storage      = 20
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  multi_az               = false
  skip_final_snapshot    = true

  tags = {
    Name = "${var.environment}-rds-mysql"
  }
}
