"""Utility functions for course operations"""
import csv
import io
from django.db import transaction
from .models import Course, CourseTopic


def import_topics_to_course(course, topics_list, description='', start_number=None, created_by=None):
    """
    Import topics for a course.
    
    Args:
        course: Course instance
        topics_list: List of topic names (strings)
        description: Default description for all topics
        start_number: Starting topic number (auto-increment if None)
        created_by: User who created the topics (optional)
    
    Returns:
        dict: {
            'imported': count,
            'skipped': count,
            'errors': list of error messages
        }
    """
    if start_number is None:
        last_topic = CourseTopic.objects.filter(course=course).order_by('-topic_number').first()
        start_number = (last_topic.topic_number + 1) if last_topic else 1
    
    imported_count = 0
    skipped_count = 0
    errors = []
    
    with transaction.atomic():
        for idx, title in enumerate(topics_list, start=start_number):
            title = title.strip()
            if not title:
                continue
            
            # Check if topic already exists (case-insensitive)
            exists = CourseTopic.objects.filter(
                course=course,
                title__iexact=title
            ).exists()
            
            if exists:
                skipped_count += 1
                continue
            
            try:
                CourseTopic.objects.create(
                    course=course,
                    title=title,
                    description=description or f'Content for {title}',
                    topic_number=idx,
                    module=None,
                    created_by=created_by,
                )
                imported_count += 1
            except Exception as e:
                skipped_count += 1
                errors.append(f'Failed to create "{title}": {str(e)}')
    
    return {
        'imported': imported_count,
        'skipped': skipped_count,
        'errors': errors
    }


def parse_csv_topics(csv_file_content):
    """
    Parse topics from CSV file content.
    
    Supports:
    - Single column: topic names only
    - Multiple columns: first column is topic name, rest ignored
    
    Args:
        csv_file_content: File-like object or string
    
    Returns:
        list: List of topic names
    """
    topics = []
    
    # Handle file upload
    if hasattr(csv_file_content, 'read'):
        content = csv_file_content.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
    else:
        content = str(csv_file_content)
    
    # Parse CSV
    reader = csv.reader(io.StringIO(content))
    for row in reader:
        if row and row[0].strip():
            topics.append(row[0].strip())
    
    return topics


def parse_text_topics(text_input):
    """
    Parse topics from newline-separated text.
    
    Args:
        text_input: String with topics separated by newlines
    
    Returns:
        list: List of topic names
    """
    topics = []
    for line in text_input.split('\n'):
        line = line.strip()
        if line:
            topics.append(line)
    return topics
