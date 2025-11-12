import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def is_ignored(path, gitignore_patterns):
    """Check if a path matches any pattern in the .gitignore."""
    # Normalize the path to ensure consistent path separators
    normalized_path = os.path.normpath(path)

    for pattern in gitignore_patterns:
        # Normalize the pattern to ensure consistent path separators
        normalized_pattern = os.path.normpath(pattern)

        # Adjust pattern to match directories
        if normalized_pattern.endswith(os.sep):
            # Match directories
            regex_pattern = re.escape(normalized_pattern[:-1]) + r'([/\\]|$)'
        else:
            # Match files or directories
            regex_pattern = re.escape(normalized_pattern) + r'([/\\]|$)'

        logging.debug(f"Checking pattern: {regex_pattern} \
            for {normalized_path}")
        try:
            # Use re.search to find the pattern anywhere in the path
            if re.search(regex_pattern, normalized_path):
                logging.debug(f"Path '{normalized_path}' is ignored due \
                    to pattern '{pattern}'.")
                return True
        except re.error as e:
            logging.error(f"Invalid regex pattern '{pattern}': {e}")
    return False


def get_gitignore_patterns(gitignore_path):
    """Read .gitignore and return a list of patterns."""
    if not os.path.exists(gitignore_path):
        logging.warning(f"Gitignore file not found at {gitignore_path}.")
        return []

    logging.info(f"Reading .gitignore from {gitignore_path}.")
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    patterns = [line.strip() for line in lines if line.strip()
                and not line.startswith('#')]
    logging.debug(f"Gitignore patterns: {patterns}")
    return patterns


def find_classes_in_file(file_path):
    """Find all class definitions in a Python file."""
    logging.info(f"Finding classes in file {file_path}.")
    class_pattern = re.compile(r'^class\s+(\w+)', re.MULTILINE)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    classes = class_pattern.findall(content)
    logging.debug(f"Classes found in {file_path}: {classes}")
    return classes


def update_init_file(directory, class_map):
    """Update or create an __init__.py file with class \
        imports and __all__ statement."""
    init_file_path = os.path.join(directory, '__init__.py')
    logging.info(f"Updating {init_file_path} with the following imports:")

    all_classes = []  # List to store all class names for __all__
    import_statements = []  # List to store import statements

    for file_name, classes in class_map.items():
        for cls in classes:
            import_statement = f'from .{file_name} import {cls}'
            logging.info(import_statement)
            import_statements.append(import_statement)
            all_classes.append(cls)

    # Construct the __all__ statement
    all_statement = f"__all__ = {all_classes}"

    # Write to the __init__.py file
    with open(init_file_path, 'w', encoding='utf-8', newline='\n') as f:
        for statement in import_statements:
            f.write(statement + '\n')
        f.write('\n' + all_statement + '\n')

    logging.info(f"Added __all__ statement: {all_statement}")


def process_directory(root_dir, gitignore_patterns):
    """Process each directory to update __init__.py files."""
    logging.info(f"Processing directory {root_dir}.")
    for root, dirs, files in os.walk(root_dir):
        if is_ignored(root, gitignore_patterns):
            logging.debug(f"Skipping ignored directory {root}.")
            continue

        class_map = {}
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                file_path = os.path.join(root, file)
                file_name = os.path.splitext(file)[0]
                classes = find_classes_in_file(file_path)
                if classes:
                    class_map[file_name] = classes

        if class_map:
            update_init_file(root, class_map)


if __name__ == "__main__":
    # Determine the directory of the script file
    script_directory = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.join(script_directory, os.pardir)
    gitignore_path = os.path.join(root_directory, '.gitignore')
    gitignore_patterns = get_gitignore_patterns(gitignore_path)
    process_directory(root_directory, gitignore_patterns)
