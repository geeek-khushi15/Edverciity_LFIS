from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.models import Course, CourseTopic


class Command(BaseCommand):
    help = 'Import topics for a specific course from a list'

    def add_arguments(self, parser):
        parser.add_argument(
            'course_id',
            type=int,
            help='Course ID to import topics into'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Default description for all topics (optional)'
        )
        parser.add_argument(
            '--start-number',
            type=int,
            default=None,
            help='Starting topic number (default: auto-increment from last)'
        )

    def handle(self, *args, **options):
        course_id = options['course_id']
        description = options['description']
        start_number = options['start_number']

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise CommandError(f'Course with ID {course_id} does not exist')

        # Full C++ syllabus topics (Topic #, Title)
        topics_list = [
            (1, "Introduction to C++"),
            (2, "History and Features of C++"),
            (3, "Structure of C++ Program"),
            (4, "Compilation & Execution Process"),
            (5, "C++ Development Environment"),
            (6, "Basic Input/Output (cin, cout)"),
            (7, "Escape Sequences"),
            (8, "Comments in C++"),
            (9, "Variables and Constants"),
            (10, "Data Types in C++"),
            (11, "Type Modifiers"),
            (12, "Type Casting"),
            (13, "Arithmetic Operators"),
            (14, "Relational Operators"),
            (15, "Logical Operators"),
            (16, "Assignment Operators"),
            (17, "Bitwise Operators"),
            (18, "Ternary Operator"),
            (19, "if Statement"),
            (20, "if-else Statement"),
            (21, "Nested if"),
            (22, "switch Case"),
            (23, "for Loop"),
            (24, "while Loop"),
            (25, "do-while Loop"),
            (26, "Nested Loops"),
            (27, "Functions in C++"),
            (28, "Function Declaration & Definition"),
            (29, "Call by Value"),
            (30, "Call by Reference"),
            (31, "Inline Functions"),
            (32, "Recursion"),
            (33, "One-Dimensional Array"),
            (34, "Two-Dimensional Array"),
            (35, "Array Operations"),
            (36, "C-style Strings"),
            (37, "String Functions"),
            (38, "C++ String Class"),
            (39, "Introduction to Pointers"),
            (40, "Pointer Arithmetic"),
            (41, "Pointers and Arrays"),
            (42, "Pointers and Functions"),
            (43, "Structures"),
            (44, "Unions"),
            (45, "Nested Structures"),
            (46, "Introduction to OOP"),
            (47, "Classes and Objects"),
            (48, "Constructors"),
            (49, "Destructors"),
            (50, "Access Specifiers"),
            (51, "Inheritance"),
            (52, "Types of Inheritance"),
            (53, "Polymorphism"),
            (54, "Function Overloading"),
            (55, "Operator Overloading"),
            (56, "Virtual Functions"),
            (57, "File Handling Basics"),
            (58, "File Modes"),
            (59, "Reading from File"),
            (60, "Writing to File"),
            (61, "Exception Handling Basics"),
            (62, "try, catch, throw"),
            (63, "Introduction to STL"),
            (64, "Vectors"),
            (65, "Lists"),
            (66, "Maps"),
            (67, "Iterators"),
        ]

        imported_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for fixed_number, title in topics_list:
                try:
                    # Respect explicit numbering from syllabus unless user provides a custom start offset.
                    topic_number = fixed_number if start_number is None else (start_number + fixed_number - 1)

                    existing = CourseTopic.objects.filter(
                        course=course,
                        module__isnull=True,
                        topic_number=topic_number,
                    ).first()

                    if existing:
                        if existing.title != title:
                            existing.title = title
                            if description:
                                existing.description = description
                            elif not (existing.description or '').strip():
                                existing.description = f'Content for {title}'
                            existing.save()
                            imported_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Updated Topic {topic_number}: "{title}"')
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'  ⊘ Skipped (already up-to-date): "{title}"')
                            )
                        continue

                    CourseTopic.objects.create(
                        course=course,
                        title=title.strip(),
                        description=description or f'Content for {title}',
                        topic_number=topic_number,
                        module=None,
                        created_by=None,
                    )
                    imported_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created Topic {topic_number}: "{title}"')
                    )
                except Exception as e:
                    skipped_count += 1
                    error_msg = f'Failed to process "{title}": {str(e)}'
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f'  ✗ {error_msg}'))

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Import complete for course "{course.title}"')
        )
        self.stdout.write(f'  Imported: {imported_count}')
        self.stdout.write(f'  Skipped:  {skipped_count}')
        if errors:
            self.stdout.write(f'  Errors:   {len(errors)}')
