"""
Core models for ReDIB COA portal.
Includes: User, Organization, Node, Equipment, UserRole
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords


class Organization(models.Model):
    """Parent organizations (ministries, universities, companies)"""

    ORG_TYPES = [
        ('university', 'University'),
        ('research_center', 'Research Center'),
        ('hospital', 'Hospital'),
        ('company', 'Company'),
        ('ministry', 'Ministry'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, default='Spain')
    organization_type = models.CharField(max_length=50, choices=ORG_TYPES)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Organizations'

    def __str__(self):
        return self.name


class Node(models.Model):
    """ReDIB network nodes (4 nodes: CICbiomaGUNE, BioImaC, La Fe, CNIC)"""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, help_text='Unique node identifier')
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    acknowledgment_text = models.TextField(
        help_text='Text to be included in publications using this node',
        blank=True
    )

    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Equipment(models.Model):
    """Essential infrastructure at each node"""

    EQUIPMENT_CATEGORIES = [
        ('mri', 'MRI'),
        ('pet', 'PET'),
        ('ct', 'CT'),
        ('pet_ct', 'PET-CT'),
        ('pet_mri', 'PET-MRI'),
        ('cyclotron', 'Cyclotron'),
        ('spect', 'SPECT'),
        ('ultrasound', 'Ultrasound'),
        ('optical', 'Optical Imaging'),
        ('other', 'Other'),
    ]

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField(max_length=100, help_text='e.g., MRI 7T, PET-CT')
    category = models.CharField(max_length=50, choices=EQUIPMENT_CATEGORIES)
    description = models.TextField(blank=True)
    technical_specs = models.TextField(blank=True, help_text='Technical specifications')

    is_essential = models.BooleanField(
        default=True,
        help_text='ICTS essential facility available for COA'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['node', 'name']
        verbose_name_plural = 'Equipment'

    def __str__(self):
        return f"{self.node.code} - {self.name}"


class User(AbstractUser):
    """Extended user with roles and affiliations"""

    # Override username field to allow email-based authentication
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)

    # Additional fields
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    orcid = models.CharField(
        max_length=20,
        blank=True,
        help_text='ORCID iD (e.g., 0000-0002-1234-5678)'
    )
    phone = models.CharField(max_length=30, blank=True)
    position = models.CharField(max_length=200, blank=True, help_text='Job title/position')

    # Email preferences
    receive_call_notifications = models.BooleanField(
        default=True,
        help_text='Receive notifications when new calls are published'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['email']

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email


class UserRole(models.Model):
    """Role assignments (users can have multiple roles)"""

    ROLES = [
        ('applicant', 'Applicant'),
        ('node_coordinator', 'Node Coordinator'),
        ('evaluator', 'Evaluator'),
        ('coordinator', 'ReDIB Coordinator'),
        ('admin', 'Administrator'),
    ]

    AREAS = [
        ('', 'Not applicable'),
        ('preclinical', 'Preclinical'),
        ('clinical', 'Clinical'),
        ('radiotracers', 'Radiotracers'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLES)
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='For node-specific roles (node_coordinator)',
        related_name='staff'
    )
    area = models.CharField(
        max_length=50,
        choices=AREAS,
        blank=True,
        help_text='Specialization area for evaluators'
    )

    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['user', 'role']
        unique_together = ['user', 'role', 'node']
        verbose_name_plural = 'User Roles'

    def __str__(self):
        if self.node:
            return f"{self.user.email} - {self.get_role_display()} at {self.node.code}"
        return f"{self.user.email} - {self.get_role_display()}"
