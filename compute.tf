resource "aws_lb" "alb" {
  name               = "prod-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  tags = {
    Name = "prod-alb"
  }
}

resource "aws_lb_target_group" "alb_tg" {
  name     = "prod-alb-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alb_tg.arn
  }
}

resource "aws_launch_template" "app_lt" {
  name_prefix   = "prod-app-lt-"
  image_id      = "ami-0c7217cdde317cfec" # Update to match your Ubuntu AMI in us-east-1
  instance_type = "t3.micro"

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_profile.name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.app_sg.id]
  }

  user_data = base64encode(<<-EOF
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y python3 python3-pip git

              # Clone application repository from GitHub
              git clone https://github.com/naveen95662/cloud-vault-app.git /home/ubuntu/app
              cd /home/ubuntu/app

              # Install dependencies
              pip3 install -r requirements.txt

              # Export Environment Variables
              export S3_BUCKET="${aws_s3_bucket.vault.id}"
              export DB_HOST="${aws_db_instance.rds.address}"
              export DB_USER="${var.db_username}"
              export DB_PASSWORD="${var.db_password}"
              export DB_NAME="${aws_db_instance.rds.db_name}"
              export AWS_REGION="us-east-1"

              # Run Flask app on port 80
              python3 app.py &
              EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "prod-app-instance"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "asg" {
  name                = "prod-asg"
  min_size            = 1
  max_size            = 2
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  target_group_arns   = [aws_lb_target_group.alb_tg.arn]

  launch_template {
    id      = aws_launch_template.app_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "prod-asg-instance"
    propagate_at_launch = true
  }
}
