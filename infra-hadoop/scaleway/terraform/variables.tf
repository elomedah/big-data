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

  validation {
    condition     = can(cidrhost(var.teacher_ssh_cidr, 0))
    error_message = "teacher_ssh_cidr must be a valid CIDR, for example \"0.0.0.0/0\" or \"203.0.113.10/32\"."
  }
}

variable "student_ssh_cidrs" {
  description = "CIDRs allowed to SSH to the student gateway."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for cidr in var.student_ssh_cidrs : can(cidrhost(cidr, 0))])
    error_message = "student_ssh_cidrs must contain only valid CIDRs, for example [\"0.0.0.0/0\"]."
  }
}

variable "student_web_cidrs" {
  description = "CIDRs allowed to access Hadoop web UIs through the gateway."
  type        = list(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = alltrue([for cidr in var.student_web_cidrs : can(cidrhost(cidr, 0))])
    error_message = "student_web_cidrs must contain only valid CIDRs, for example [\"0.0.0.0/0\"]."
  }
}

variable "private_cidr" {
  description = "Private network CIDR used for security group rules."
  type        = string
  default     = "10.42.0.0/16"

  validation {
    condition     = can(cidrhost(var.private_cidr, 0))
    error_message = "private_cidr must be a valid CIDR, for example \"10.42.0.0/16\"."
  }
}

variable "private_subnet" {
  description = "Private subnet reserved in Scaleway IPAM for the Hadoop cluster."
  type        = string
  default     = "10.42.0.0/24"

  validation {
    condition     = can(cidrhost(var.private_subnet, 0))
    error_message = "private_subnet must be a valid CIDR, for example \"10.42.0.0/24\"."
  }
}

variable "allocate_public_ip_to_private_nodes" {
  description = "Attach public IPs to private Hadoop nodes for outbound internet during provisioning. Inbound traffic is still controlled by security groups."
  type        = bool
  default     = true
}

variable "worker_mode" {
  description = "Worker compute mode: active for TP sessions, reduced outside TP while keeping data volumes."
  type        = string
  default     = "active"

  validation {
    condition     = contains(["active", "reduced"], var.worker_mode)
    error_message = "worker_mode must be either active or reduced."
  }
}

variable "worker_active_commercial_type" {
  description = "Scaleway instance type used by Hadoop workers when worker_mode is active."
  type        = string
  default     = "DEV1-S"
}

variable "worker_reduced_commercial_type" {
  description = "Scaleway instance type used by Hadoop workers when worker_mode is reduced."
  type        = string
  default     = "DEV1-S"
}

variable "large_worker_data_size_gb" {
  description = "HDFS Block Storage size in GB attached to each worker in the large teaching profile."
  type        = number
  default     = 100

  validation {
    condition     = var.large_worker_data_size_gb >= 5
    error_message = "large_worker_data_size_gb must be at least 5 GB."
  }
}

variable "tiny_worker_count" {
  description = "Number of Hadoop workers created by the tiny test profile."
  type        = number
  default     = 3

  validation {
    condition     = var.tiny_worker_count >= 1 && var.tiny_worker_count <= 20
    error_message = "tiny_worker_count must be between 1 and 20."
  }
}

variable "large_worker_count" {
  description = "Number of Hadoop workers created by the large teaching profile."
  type        = number
  default     = 5

  validation {
    condition     = var.large_worker_count >= 1 && var.large_worker_count <= 20
    error_message = "large_worker_count must be between 1 and 20."
  }
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
