variable "project_name" {
  description = "Prefix used for Scaleway resource names."
  type        = string
  default     = "m2-hadoop"
}

variable "region" {
  description = "Scaleway region."
  type        = string
  default     = "fr-par"
}

variable "zone" {
  description = "Scaleway availability zone."
  type        = string
  default     = "fr-par-1"
}

variable "image" {
  description = "Base image label or UUID."
  type        = string
  default     = "ubuntu_jammy"
}

variable "admin_ssh_public_key_path" {
  description = "Path to the public SSH key injected into every server."
  type        = string
  default     = "~/.ssh/m2-hadoop-scaleway.pub"
}

variable "teacher_ssh_cidr" {
  description = "CIDR allowed to SSH to the bastion."
  type        = string
}

variable "student_ssh_cidrs" {
  description = "CIDRs allowed to SSH to the student gateway."
  type        = list(string)
  default     = []
}

variable "private_cidr" {
  description = "Private network CIDR used for security group rules."
  type        = string
  default     = "10.42.0.0/16"
}

variable "private_subnet" {
  description = "Private subnet reserved in Scaleway IPAM for the Hadoop cluster."
  type        = string
  default     = "10.42.0.0/24"
}

variable "student_count" {
  description = "Number of student Linux/HDFS accounts to prepare."
  type        = number
  default     = 30
}

variable "cluster_size" {
  description = "Sizing profile to use: tiny for tests, large for the teaching cluster."
  type        = string
  default     = "tiny"

  validation {
    condition     = contains(["tiny", "large"], var.cluster_size)
    error_message = "cluster_size must be either tiny or large."
  }
}
