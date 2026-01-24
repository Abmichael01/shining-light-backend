from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from api.models.cbt import Question
import datetime
import os
from pathlib import Path

class Command(BaseCommand):
    help = 'Cleans up orphaned uploaded files that are not referenced in Questions'

    def handle(self, *args, **options):
        self.stdout.write("Starting cleanup...")
        
        # 1. Gather all file references from Questions (text, explanation, options)
        questions = Question.objects.all()
        referenced_files = set()
        
        # We look for the filename in the text content
        # Note: This is a simple substring check. 
        # If absolute URLs are saved, we match the filename part.
        
        # In B2/S3, storage.url returns full URL. 
        # In local, it returns relative or absolute URI.
        # Key is to list files in storage and check if their name appears in content.
        
        # Let's list files in uploads/
        # Note: default_storage.listdir might behave differently on B2 vs Local
        try:
            dirs, files = default_storage.listdir('uploads')
        except OSError:
            # Maybe uploads directory doesn't exist yet
            self.stdout.write("Uploads directory not found or empty.")
            return

        self.stdout.write(f"Found {len(files)} files in uploads/")
        
        if not files:
            return

        # Prepare content strings for searching
        # Concatenate all content into one massive string or iterate
        # Iterating might be better for memory if many questions
        
        # Optimization: Fetch only text fields
        question_data = questions.values_list('question_text', 'explanation', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e')
        
        orphaned_count = 0
        
        threshold = timezone.now() - datetime.timedelta(hours=24)
        
        for filename in files:
            # Skip if file is new (less than 24h) to avoid race conditions with being-written questions
            full_path = os.path.join('uploads', filename)
            try:
                # default_storage.get_created_time might not be supported on all backends, 
                # modified_time is safer
                modified_time = default_storage.get_modified_time(full_path)
                if modified_time > threshold:
                    continue
            except NotImplementedError:
                # If backend doesn't support time check, assume unsafe to delete unless very sure
                # Or skip time check if we trust the reference check completely
                pass
            except Exception as e:
                self.stderr.write(f"Error checking time for {filename}: {e}")
                continue

            # Check if referenced
            is_referenced = False
            
            # Simple check: is the filename present in any content?
            # This is O(N*M) where N=files, M=questions. Could be slow.
            # Faster: Construct a big set of all content text? No, too big.
            # Faster: Construct a set of all *likely* filenames from content?
            # Regex or parsing HTML to extract img src is precise but also slow.
            # Given the scale (school), simple iteration might pass for now.
            
            # Better approach:
            # 1. Create a set of all filenames used in the DB.
            #    We can use a regex to extract all image sources from the text fields.
            
            # Implementation of Better approach:
            
            # This logic below uses the "check each file" approach but optimizes by doing it in batch if needed
            # But let's stick to simple iteration for now, safe and robust code.
            
            for q_text, expl, opt_a, opt_b, opt_c, opt_d, opt_e in question_data:
                # Naive string check
                if (q_text and filename in q_text) or \
                   (expl and filename in expl) or \
                   (opt_a and filename in opt_a) or \
                   (opt_b and filename in opt_b) or \
                   (opt_c and filename in opt_c) or \
                   (opt_d and filename in opt_d) or \
                   (opt_e and filename in opt_e):
                    is_referenced = True
                    break
            
            if not is_referenced:
                self.stdout.write(f"Deleting orphaned file: {filename}")
                default_storage.delete(full_path)
                orphaned_count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Cleanup complete. Deleted {orphaned_count} files."))
