#!/usr/bin/env python3
"""
Python script to compile all .py files in the project
Replaces the shell 'find' command that's not available
"""

import os
import py_compile
import sys

def compile_python_files(directory='.'):
    """Recursively find and compile all Python files"""
    compiled_count = 0
    error_count = 0
    
    print(f"🔍 Searching for Python files in: {os.path.abspath(directory)}")
    
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    py_compile.compile(file_path, doraise=True)
                    print(f"✅ Compiled: {file_path}")
                    compiled_count += 1
                except py_compile.PyCompileError as e:
                    print(f"❌ Error compiling {file_path}: {e}")
                    error_count += 1
                except Exception as e:
                    print(f"❌ Unexpected error compiling {file_path}: {e}")
                    error_count += 1
    
    print(f"\n📊 Compilation Summary:")
    print(f"✅ Successfully compiled: {compiled_count} files")
    print(f"❌ Errors: {error_count} files")
    
    if error_count > 0:
        print(f"\n⚠️  Please fix the errors above before running the bot")
        return False
    else:
        print(f"\n🎉 All Python files compiled successfully!")
        return True

if __name__ == "__main__":
    success = compile_python_files()
    sys.exit(0 if success else 1)