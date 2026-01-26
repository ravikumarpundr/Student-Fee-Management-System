import os
import shutil
import json
import sqlite3
from datetime import datetime
from database import get_setting, set_setting, delete_setting
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QSpinBox, QFileDialog, QGroupBox, QTabWidget, QTextEdit,
    QProgressBar, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# Dropbox imports (optional - will handle gracefully if not installed)
try:
    import dropbox
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

class LoadingOverlay(QFrame):
    """Professional loading overlay with spinner and message"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Make it a proper overlay within the parent window
        self.setWindowFlags(Qt.Widget)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        # Simple loading indicator (no animation)
        self.loading_indicator = QLabel("⏳")
        self.loading_indicator.setFixedSize(60, 60)
        self.loading_indicator.setStyleSheet("""
            QLabel {
                background-color: transparent;
                font-size: 24px;
                color: #3498db;
                font-weight: bold;
            }
        """)
        self.loading_indicator.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_indicator, 0, Qt.AlignCenter)
        
        # Loading text
        self.loading_label = QLabel("Backup in Progress...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # Warning message
        self.warning_label = QLabel("Please do not close this window")
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #f39c12;
                font-size: 12px;
                font-weight: 500;
                background-color: transparent;
            }
        """)
        self.warning_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.warning_label)
        
        self.setLayout(layout)
        
    def show_overlay(self, message="Backup in Progress..."):
        """Show the loading overlay"""
        self.loading_label.setText(message)
        # Position overlay to cover the entire parent window
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
            self.raise_()
        self.show()
        
    def hide_overlay(self):
        """Hide the loading overlay"""
        self.hide()
        
    def update_message(self, message):
        """Update the loading message"""
        self.loading_label.setText(message)

class BackupWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Changed to emit detailed results
    
    def __init__(self, operation_type, config):
        super().__init__()
        self.operation_type = operation_type  # 'backup' or 'restore'
        self.config = config
        
    def run(self):
        try:
            if self.operation_type == "backup":
                self.status.emit("Starting backup operations...")
                results = self.perform_backup()
            elif self.operation_type == "restore":
                self.status.emit("Starting restore operations...")
                results = self.perform_restore()
            else:
                results = {"success": False, "message": "Invalid operation type"}
                
            self.finished.emit(results)
        except Exception as e:
            self.finished.emit({"success": False, "message": f"Operation failed: {str(e)}"})
    
    def perform_backup(self):
        """Perform backup on both local and Dropbox if configured"""
        results = {
            "success": True,
            "local": {"success": False, "message": ""},
            "dropbox": {"success": False, "message": ""},
            "summary": ""
        }
        
        # Check if local backup is configured
        local_path = self.config.get('local_path', '').strip()
        dropbox_token = self.config.get('dropbox_token', '').strip()
        
        if not local_path and not dropbox_token:
            return {
                "success": False,
                "message": "No backup methods configured. Please set up local path or Dropbox token."
            }
        
        # Perform local backup if configured
        if local_path:
            self.status.emit("Performing local backup...")
            try:
                results["local"] = self.local_backup()
                if results["local"]["success"]:
                    self.status.emit(f"✅ Local backup successful: {results['local']['message']}")
                else:
                    self.status.emit(f"❌ Local backup failed: {results['local']['message']}")
            except Exception as e:
                error_msg = f"Local backup failed: {str(e)}"
                results["local"] = {"success": False, "message": error_msg}
                self.status.emit(f"❌ {error_msg}")
        
        # Perform Dropbox backup if configured
        if dropbox_token:
            self.status.emit("Performing Dropbox backup...")
            try:
                results["dropbox"] = self.dropbox_backup()
                if results["dropbox"]["success"]:
                    self.status.emit(f"✅ Dropbox backup successful: {results['dropbox']['message']}")
                else:
                    self.status.emit(f"❌ Dropbox backup failed: {results['dropbox']['message']}")
            except Exception as e:
                error_msg = f"Dropbox backup failed: {str(e)}"
                results["dropbox"] = {"success": False, "message": error_msg}
                self.status.emit(f"❌ {error_msg}")
        
        # Generate summary
        local_status = "✅ Success" if results["local"]["success"] else "❌ Failed"
        dropbox_status = "✅ Success" if results["dropbox"]["success"] else "❌ Failed"
        
        if local_path and dropbox_token:
            results["summary"] = f"Local: {local_status} | Dropbox: {dropbox_status}"
        elif local_path:
            results["summary"] = f"Local: {local_status}"
        else:
            results["summary"] = f"Dropbox: {dropbox_status}"
        
        # Overall success if at least one backup succeeded
        results["success"] = results["local"]["success"] or results["dropbox"]["success"]
        
        return results
    
    def perform_restore(self):
        """Perform restore operation"""
        results = {
            "success": True,
            "message": "Restore completed successfully",
            "local": {"success": False, "message": ""},
            "dropbox": {"success": False, "message": ""}
        }
        
        # Try local restore first
        local_path = self.config.get('local_path', '')
        if local_path and os.path.exists(local_path):
            try:
                self.status.emit("Attempting local restore...")
                local_result = self.local_restore()
                results["local"] = local_result
                if local_result["success"]:
                    self.status.emit(f"✅ Local restore successful: {local_result['message']}")
                else:
                    self.status.emit(f"❌ Local restore failed: {local_result['message']}")
            except Exception as e:
                error_msg = f"Local restore failed: {str(e)}"
                results["local"] = {"success": False, "message": error_msg}
                self.status.emit(f"❌ {error_msg}")
        
        # Try Dropbox restore if local failed or not configured
        if not results["local"]["success"]:
            dropbox_token = self.config.get('dropbox_token', '')
            if dropbox_token:
                try:
                    self.status.emit("Attempting Dropbox restore...")
                    dropbox_result = self.dropbox_restore()
                    results["dropbox"] = dropbox_result
                    if dropbox_result["success"]:
                        self.status.emit(f"✅ Dropbox restore successful: {dropbox_result['message']}")
                    else:
                        self.status.emit(f"❌ Dropbox restore failed: {dropbox_result['message']}")
                except Exception as e:
                    error_msg = f"Dropbox restore failed: {str(e)}"
                    results["dropbox"] = {"success": False, "message": error_msg}
                    self.status.emit(f"❌ {error_msg}")
        
        # Determine overall success
        if results["local"]["success"] or results["dropbox"]["success"]:
            results["success"] = True
            results["message"] = "Restore completed successfully"
        else:
            results["success"] = False
            results["message"] = "Restore failed - no valid backups found"
        
        return results
    
    def local_restore(self):
        """Restore from local backup"""
        try:
            backup_dir = self.config.get('local_path', '')
            
            if not backup_dir or not os.path.exists(backup_dir):
                return {"success": False, "message": "Local backup directory not found"}
            
            # Find the most recent backup file
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith("institute_backup_") and filename.endswith(".db"):
                    file_path = os.path.join(backup_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    # Also extract timestamp from filename as fallback
                    try:
                        # Extract timestamp from filename: institute_backup_YYYYMMDD_HHMMSS.db
                        timestamp_str = filename.replace("institute_backup_", "").replace(".db", "")
                        filename_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        backup_files.append((mtime, file_path, filename, filename_timestamp))
                    except:
                        # If timestamp parsing fails, just use file modification time
                        backup_files.append((mtime, file_path, filename, None))
            
            if not backup_files:
                return {"success": False, "message": "No backup files found in local directory"}
            
            # Sort by modification time (newest first), with filename timestamp as tiebreaker
            backup_files.sort(key=lambda x: (x[0], x[3] if x[3] else datetime.min), reverse=True)
            latest_backup_path = backup_files[0][1]
            latest_backup_name = backup_files[0][2]
            
            # Debug: Log which backup is being restored
            print(f"Found {len(backup_files)} backup files. Restoring from: {latest_backup_name}")
            print(f"Backup files found: {[f[2] for f in backup_files[:3]]}")  # Show first 3
            
            # Create backup of current database before restore
            current_db_path = "institute.db"
            if os.path.exists(current_db_path):
                backup_current_path = f"institute_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy2(current_db_path, backup_current_path)
            
            # Restore the database
            shutil.copy2(latest_backup_path, current_db_path)
            
            # Verify the restored database is valid
            try:
                import sqlite3
                test_conn = sqlite3.connect(current_db_path)
                test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                test_conn.close()
            except Exception as e:
                return {"success": False, "message": f"Restored database is corrupted: {str(e)}"}
            
            return {"success": True, "message": f"Restored from local backup: {latest_backup_name}"}
            
        except Exception as e:
            return {"success": False, "message": f"Local restore failed: {str(e)}"}
    
    def dropbox_restore(self):
        """Restore from Dropbox backup"""
        try:
            if not DROPBOX_AVAILABLE:
                return {"success": False, "message": "Dropbox SDK not installed"}
            
            access_token = self.config.get('dropbox_token', '')
            if not access_token:
                return {"success": False, "message": "Dropbox token not configured"}
            
            # Initialize Dropbox client
            dbx = dropbox.Dropbox(access_token)
            
            # List backup files in Dropbox
            try:
                result = dbx.files_list_folder("/InstituteBackups")
                backup_files = []
                
                for entry in result.entries:
                    if entry.name.startswith("institute_backup_") and entry.name.endswith(".db"):
                        # Also extract timestamp from filename as fallback
                        try:
                            # Extract timestamp from filename: institute_backup_YYYYMMDD_HHMMSS.db
                            timestamp_str = entry.name.replace("institute_backup_", "").replace(".db", "")
                            filename_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            backup_files.append((entry.name, entry.server_modified, filename_timestamp))
                        except:
                            # If timestamp parsing fails, just use server modification time
                            backup_files.append((entry.name, entry.server_modified, None))
                
                if not backup_files:
                    return {"success": False, "message": "No backup files found in Dropbox"}
                
                # Sort by server modification time (newest first), with filename timestamp as tiebreaker
                backup_files.sort(key=lambda x: (x[1], x[2] if x[2] else datetime.min), reverse=True)
                latest_backup_name = backup_files[0][0]
                
                # Debug: Log which backup is being restored
                print(f"Found {len(backup_files)} Dropbox backup files. Restoring from: {latest_backup_name}")
                print(f"Dropbox backup files found: {[f[0] for f in backup_files[:3]]}")  # Show first 3
                
                # Download the latest backup
                backup_path = f"/InstituteBackups/{latest_backup_name}"
                metadata, response = dbx.files_download(backup_path)
                
                # Create backup of current database before restore
                current_db_path = "institute.db"
                if os.path.exists(current_db_path):
                    backup_current_path = f"institute_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    shutil.copy2(current_db_path, backup_current_path)
                
                # Write the downloaded backup to current database
                with open(current_db_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify the restored database is valid
                try:
                    import sqlite3
                    test_conn = sqlite3.connect(current_db_path)
                    test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    test_conn.close()
                except Exception as e:
                    return {"success": False, "message": f"Restored database is corrupted: {str(e)}"}
                
                return {"success": True, "message": f"Restored from Dropbox backup: {latest_backup_name}"}
                
            except dropbox.exceptions.ApiError as e:
                return {"success": False, "message": f"Dropbox API error: {str(e)}"}
                
        except Exception as e:
            return {"success": False, "message": f"Dropbox restore failed: {str(e)}"}
    
    def local_backup(self):
        try:
            backup_dir = self.config.get('local_path', '')
            max_revisions = self.config.get('max_revisions', 5)
            
            if not backup_dir:
                return {"success": False, "message": "Local backup path not configured"}
            
            # Check if directory exists or can be created
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except PermissionError:
                return {"success": False, "message": f"Permission denied: Cannot create directory '{backup_dir}'"}
            except OSError as e:
                return {"success": False, "message": f"Cannot access directory '{backup_dir}': {str(e)}"}
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"institute_backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Check if database file exists
            db_path = "institute.db"
            if not os.path.exists(db_path):
                return {"success": False, "message": f"Database file '{db_path}' not found in current directory"}
            
            # Check available disk space
            try:
                statvfs = os.statvfs(backup_dir)
                free_space = statvfs.f_frsize * statvfs.f_bavail
                db_size = os.path.getsize(db_path)
                if free_space < db_size * 2:  # Need at least 2x the database size
                    return {"success": False, "message": f"Insufficient disk space. Available: {free_space//1024//1024}MB, Required: {db_size//1024//1024}MB"}
            except:
                pass  # Skip disk space check if not available
            
            # Copy database file
            try:
                shutil.copy2(db_path, backup_path)
            except PermissionError:
                return {"success": False, "message": f"Permission denied: Cannot write to '{backup_path}'"}
            except OSError as e:
                return {"success": False, "message": f"Failed to copy database: {str(e)}"}
            
            # Clean up old backups
            try:
                self.cleanup_old_backups(backup_dir, max_revisions)
            except Exception as e:
                # Don't fail the backup if cleanup fails, but log it
                print(f"Warning: Failed to cleanup old backups: {str(e)}")
            
            return {"success": True, "message": f"Local backup created: {backup_filename}"}
            
        except Exception as e:
            return {"success": False, "message": f"Local backup failed: {str(e)}"}
    
    def cleanup_old_backups(self, backup_dir, max_revisions):
        """Clean up old backup files to maintain revision limit"""
        try:
            # Get all backup files
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith("institute_backup_") and filename.endswith(".db"):
                    file_path = os.path.join(backup_dir, filename)
                    # Get file modification time
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((mtime, file_path, filename))
            
            # Sort by modification time (newest first)
            backup_files.sort(reverse=True)
            
            # Remove excess backups
            removed_count = 0
            if len(backup_files) > max_revisions:
                files_to_remove = backup_files[max_revisions:]
                for _, file_path, filename in files_to_remove:
                    try:
                        os.remove(file_path)
                        removed_count += 1
                        print(f"Removed old backup: {filename}")
                    except Exception as e:
                        print(f"Failed to remove {filename}: {str(e)}")
            
            if removed_count > 0:
                print(f"Cleanup completed: Removed {removed_count} old backup(s), keeping {max_revisions} most recent")
                        
        except Exception as e:
            print(f"Cleanup failed: {str(e)}")
    
    def dropbox_backup(self):
        try:
            if not DROPBOX_AVAILABLE:
                return {"success": False, "message": "Dropbox SDK not installed. Run: pip install dropbox"}
            
            access_token = self.config.get('dropbox_token', '')
            max_revisions = self.config.get('max_revisions', 5)
            
            if not access_token:
                return {"success": False, "message": "Dropbox token not configured"}
            
            # Initialize Dropbox client
            try:
                dbx = dropbox.Dropbox(access_token)
            except Exception as e:
                return {"success": False, "message": f"Failed to initialize Dropbox client: {str(e)}"}
            
            # Test connection and permissions first
            try:
                # Try to list files to test permissions
                dbx.files_list_folder("")
            except dropbox.exceptions.AuthError as e:
                return {"success": False, "message": f"Invalid Dropbox token. Please check your token and try again.\n\nError details: {str(e)}"}
            except dropbox.exceptions.ApiError as e:
                if "scope" in str(e).lower() or "permitted" in str(e).lower():
                    return {"success": False, "message": f"Missing Dropbox permissions. Please enable these scopes in your Dropbox app:\n\n- files.content.write\n- files.metadata.write\n- files.content.read\n- files.metadata.read\n\nThen generate a new token.\n\nError details: {str(e)}"}
                else:
                    return {"success": False, "message": f"Dropbox API error: {str(e)}"}
            except Exception as e:
                return {"success": False, "message": f"Failed to connect to Dropbox: {str(e)}"}
            
            # Generate incremental backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"institute_backup_{timestamp}.db"
            
            # Create incremental backup
            try:
                backup_data = self.create_incremental_backup()
            except Exception as e:
                return {"success": False, "message": f"Failed to create backup data: {str(e)}"}
            
            # Create backup folder if it doesn't exist
            try:
                dbx.files_create_folder("/InstituteBackups")
            except dropbox.exceptions.ApiError as e:
                if "conflict" not in str(e).lower():
                    return {"success": False, "message": f"Failed to create backup folder: {str(e)}"}
                # Folder already exists, which is fine
            
            # Upload to Dropbox
            try:
                backup_path = f"/InstituteBackups/{backup_filename}"
                dbx.files_upload(backup_data, backup_path, mode=dropbox.files.WriteMode.overwrite)
            except dropbox.exceptions.ApiError as e:
                return {"success": False, "message": f"Failed to upload backup to Dropbox: {str(e)}"}
            except Exception as e:
                return {"success": False, "message": f"Upload failed: {str(e)}"}
            
            # Update backup index
            try:
                self.update_backup_index(dbx, backup_filename, timestamp)
            except Exception as e:
                # Don't fail the backup if index update fails
                pass
            
            # Clean up old Dropbox backups
            try:
                self.cleanup_dropbox_backups(dbx, max_revisions)
            except Exception as e:
                # Don't fail the backup if cleanup fails
                pass
            
            return {"success": True, "message": f"Dropbox backup uploaded successfully: {backup_filename}"}
            
        except Exception as e:
            return {"success": False, "message": f"Dropbox backup failed: {str(e)}"}
    
    def create_incremental_backup(self):
        """Create simple database backup (not compressed)"""
        try:
            import sqlite3
            import tempfile
            
            # Source database path
            source_db_path = "institute.db"
            if not os.path.exists(source_db_path):
                raise Exception("Database file not found")
            
            # Create temporary backup database
            temp_backup_path = tempfile.mktemp(suffix='.db')
            
            try:
                # Connect to source database
                source_conn = sqlite3.connect(source_db_path)
                
                # Create backup database
                backup_conn = sqlite3.connect(temp_backup_path)
                
                # Use SQLite's backup API to create a proper database file
                def progress_callback(status, remaining, total):
                    # Optional: Update progress if needed
                    pass
                
                # Perform backup - creates a proper database file
                source_conn.backup(backup_conn, pages=1, progress=progress_callback)
                
                # Close connections
                source_conn.close()
                backup_conn.close()
                
                # Read the backup file (don't compress - keep as regular database)
                with open(temp_backup_path, 'rb') as f:
                    backup_data = f.read()
                
                return backup_data
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_backup_path)
                except:
                    pass
            
        except Exception as e:
            # Clean up temporary file if it exists
            try:
                if 'temp_backup_path' in locals():
                    os.unlink(temp_backup_path)
            except:
                pass
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def get_last_backup_timestamp(self):
        """Get timestamp of last successful backup"""
        try:
            if os.path.exists("backup_index.json"):
                with open("backup_index.json", "r") as f:
                    index = json.load(f)
                    return index.get('last_backup_timestamp')
        except:
            pass
        return None
    
    def update_backup_index(self, dbx, backup_filename, timestamp):
        """Update backup index file"""
        try:
            index_data = {
                'last_backup_timestamp': timestamp,
                'last_backup_file': backup_filename,
                'backup_count': self.get_backup_count() + 1
            }
            
            # Save locally
            with open("backup_index.json", "w") as f:
                json.dump(index_data, f)
            
            # Upload to Dropbox
            index_json = json.dumps(index_data)
            dbx.files_upload(index_json.encode('utf-8'), "/InstituteBackups/backup_index.json", 
                           mode=dropbox.files.WriteMode.overwrite)
            
        except Exception as e:
            print(f"Warning: Could not update backup index: {e}")
    
    def get_backup_count(self):
        """Get current backup count"""
        try:
            if os.path.exists("backup_index.json"):
                with open("backup_index.json", "r") as f:
                    index = json.load(f)
                    return index.get('backup_count', 0)
        except:
            pass
        return 0
    
    def cleanup_dropbox_backups(self, dbx, max_revisions):
        """Remove old Dropbox backup files"""
        try:
            # List all backup files
            result = dbx.files_list_folder("/InstituteBackups")
            backup_files = []
            
            for entry in result.entries:
                if entry.name.startswith("institute_backup_") and entry.name.endswith(".db"):
                    backup_files.append((entry.name, entry.server_modified))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Delete excess backups
            for filename, _ in backup_files[max_revisions:]:
                try:
                    dbx.files_delete(f"/InstituteBackups/{filename}")
                except:
                    pass  # File might already be deleted
                    
        except Exception as e:
            print(f"Error cleaning up Dropbox backups: {e}")

class SettingsManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 800, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2c3e50;
            }
            QLabel {
                color: #2c3e50;
                font-weight: 600;
                font-size: 12px;
                margin: 5px 0px;
                background-color: transparent;
            }
            QLineEdit {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                color: #495057;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                color: white;
            }
            QPushButton:pressed {
                background-color: #21618c;
                color: white;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #2c3e50;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
                color: #2c3e50;
            }
            QSpinBox {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                color: #495057;
            }
            QTextEdit {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                font-family: 'Courier New', monospace;
                color: #495057;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Title section
        title_label = QLabel("Settings & Backup")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0px 20px 0px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_backup_tab()
        self.create_general_tab()

        # Status area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setPlaceholderText("Status messages will appear here...")
        layout.addWidget(self.status_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()
        
        # Store references to buttons for enabling/disabling
        self.backup_button = None
        self.restore_button = None
        self.save_button = None
        
        self.load_settings()

    def show_loading_overlay(self, message="Backup in Progress..."):
        """Show loading overlay and disable buttons"""
        # Ensure the main window stays visible
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Show the loading overlay
        self.loading_overlay.show_overlay(message)
        
        # Disable all buttons
        if self.backup_button:
            self.backup_button.setEnabled(False)
        if self.restore_button:
            self.restore_button.setEnabled(False)
        if self.save_button:
            self.save_button.setEnabled(False)
        
        # Disable window close
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
    def hide_loading_overlay(self):
        """Hide loading overlay and enable buttons"""
        self.loading_overlay.hide_overlay()
        
        # Enable all buttons
        if self.backup_button:
            self.backup_button.setEnabled(True)
        if self.restore_button:
            self.restore_button.setEnabled(True)
        if self.save_button:
            self.save_button.setEnabled(True)
        
        # Enable window close
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)

    def create_backup_tab(self):
        """Create the backup configuration tab"""
        backup_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # General backup settings
        general_group = QGroupBox("General Backup Settings")
        general_layout = QVBoxLayout()
        
        revisions_layout = QHBoxLayout()
        revisions_label = QLabel("Max Revisions to Keep:")
        revisions_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        revisions_layout.addWidget(revisions_label)
        self.max_revisions_spin = QSpinBox()
        self.max_revisions_spin.setRange(1, 20)
        self.max_revisions_spin.setValue(5)
        revisions_layout.addWidget(self.max_revisions_spin)
        revisions_layout.addStretch()
        general_layout.addLayout(revisions_layout)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Local backup settings
        local_group = QGroupBox("Local Drive Backup")
        local_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        path_label = QLabel("Backup Path:")
        path_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        path_layout.addWidget(path_label)
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText("Select backup directory...")
        path_layout.addWidget(self.local_path_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_local_path)
        path_layout.addWidget(browse_btn)
        local_layout.addLayout(path_layout)
        
        local_group.setLayout(local_layout)
        layout.addWidget(local_group)

        # Dropbox backup settings
        dropbox_group = QGroupBox("Dropbox Cloud Backup")
        dropbox_layout = QVBoxLayout()
        
        token_layout = QHBoxLayout()
        token_label = QLabel("Dropbox Access Token:")
        token_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        token_layout.addWidget(token_label)
        self.dropbox_token_input = QLineEdit()
        self.dropbox_token_input.setPlaceholderText("Enter your Dropbox access token...")
        self.dropbox_token_input.setEchoMode(QLineEdit.Password)
        token_layout.addWidget(self.dropbox_token_input)
        
        help_btn = QPushButton("Help")
        help_btn.clicked.connect(self.show_dropbox_help)
        help_btn.setFixedWidth(60)
        token_layout.addWidget(help_btn)
        dropbox_layout.addLayout(token_layout)
        
        help_text = QLabel("Get your token from: https://www.dropbox.com/developers/apps")
        help_text.setStyleSheet("color: #7f8c8d; font-size: 10px; font-style: italic;")
        dropbox_layout.addWidget(help_text)
        
        dropbox_group.setLayout(dropbox_layout)
        layout.addWidget(dropbox_group)
        
        # Action buttons section
        action_group = QGroupBox("Backup & Restore Operations")
        action_layout = QVBoxLayout()
        
        # Backup button
        self.backup_button = QPushButton("Create Backup")
        self.backup_button.clicked.connect(self.start_backup)
        self.backup_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        action_layout.addWidget(self.backup_button)
        
        # Restore button
        self.restore_button = QPushButton("Restore from Backup")
        self.restore_button.clicked.connect(self.start_restore)
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        action_layout.addWidget(self.restore_button)
        
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        # Save settings button
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        layout.addStretch()
        backup_tab.setLayout(layout)
        self.tab_widget.addTab(backup_tab, "Backup")

    def create_general_tab(self):
        """Create the general settings tab"""
        general_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Database info
        db_group = QGroupBox("Database Information")
        db_layout = QVBoxLayout()
        
        db_info = QLabel("Database: SQLite (institute.db)")
        db_info.setStyleSheet("color: #27ae60; font-weight: bold; font-size: 14px;")
        db_layout.addWidget(db_info)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # Application info
        app_group = QGroupBox("Application Information")
        app_layout = QVBoxLayout()
        
        app_info = QLabel("Institute Management System v1.0")
        app_info.setStyleSheet("color: #2c3e50; font-weight: bold; font-size: 14px;")
        app_layout.addWidget(app_info)
        
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()
        general_tab.setLayout(layout)
        self.tab_widget.addTab(general_tab, "General")

    def browse_local_path(self):
        """Browse for local backup directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if directory:
            self.local_path_input.setText(directory)

    def show_dropbox_help(self):
        """Show help for getting Dropbox token"""
        help_text = """
How to get your Dropbox Access Token:

1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose "Scoped access" and "Full Dropbox"
4. Give your app a name (e.g., "Institute Backup")
5. After creating, go to "Permissions" tab
6. REQUIRED: Enable these permissions:
   - files.metadata.write
   - files.content.write
   - files.metadata.read
   - files.content.read
7. Click "Submit" to save permissions
8. Go to "Settings" tab and generate access token
9. Copy the token and paste it above

IMPORTANT: Make sure to enable ALL required permissions
before generating the token, otherwise backup will fail.

The token will be stored securely in your settings.
        """
        QMessageBox.information(self, "Dropbox Setup Help", help_text)

    def start_backup(self):
        """Start backup operation"""
        config = self.get_secure_config()
        
        if not config.get('local_path', '').strip() and not config.get('dropbox_token', '').strip():
            QMessageBox.warning(self, "Configuration Error", 
                              "No backup methods configured.\nPlease set up local path or Dropbox token first.")
            return
        
        # Show loading overlay
        self.show_loading_overlay("Starting backup operations...")
        
        # Start backup worker
        self.backup_worker = BackupWorker("backup", config)
        self.backup_worker.progress.connect(self.update_progress)
        self.backup_worker.status.connect(self.update_loading_message)
        self.backup_worker.finished.connect(self.backup_finished)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.update_status("Starting backup operations...")
        
        self.backup_worker.start()
    
    def start_restore(self):
        """Start restore operation"""
        reply = QMessageBox.question(self, 'Confirm Restore', 
                                   'Are you sure you want to restore from backup?\nThis will replace your current database.',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            config = self.get_secure_config()
            
            # Show loading overlay
            self.show_loading_overlay("Starting restore operations...")
            
            # Start restore worker
            self.backup_worker = BackupWorker("restore", config)
            self.backup_worker.progress.connect(self.update_progress)
            self.backup_worker.status.connect(self.update_loading_message)
            self.backup_worker.finished.connect(self.restore_finished)
            
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.update_status("Starting restore operations...")
            
            self.backup_worker.start()
    
    def update_loading_message(self, message):
        """Update both status text and loading overlay message"""
        self.update_status(message)
        self.loading_overlay.update_message(message)
    
    def get_secure_config(self):
        """Get configuration from database"""
        config = {
            'local_path': self.local_path_input.text().strip(),
            'max_revisions': self.max_revisions_spin.value()
        }
        
        # Get Dropbox token from database
        dropbox_token = get_setting('dropbox_token', '')
        config['dropbox_token'] = dropbox_token
        
        return config

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """Update status text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")

    def backup_finished(self, results):
        """Handle backup completion"""
        self.progress_bar.setVisible(False)
        self.hide_loading_overlay()  # Hide loading overlay and enable buttons
        
        if results.get("success"):
            # Show detailed results
            message = f"Backup completed!\n\n{results.get('summary', '')}"
            
            # Add detailed messages
            if "local" in results and results["local"]["message"]:
                message += f"\n\nLocal: {results['local']['message']}"
            if "dropbox" in results and results["dropbox"]["message"]:
                message += f"\n\nDropbox: {results['dropbox']['message']}"
            
            self.update_status(f"✅ {results.get('summary', 'Backup completed')}")
            QMessageBox.information(self, "Backup Complete", message)
        else:
            # Show detailed error information
            error_msg = results.get("message", "Backup failed")
            
            # Build detailed error message
            detailed_msg = f"Backup failed!\n\n{error_msg}"
            
            # Add individual error details
            if "local" in results and not results["local"]["success"]:
                detailed_msg += f"\n\nLocal Backup Error:\n{results['local']['message']}"
            if "dropbox" in results and not results["dropbox"]["success"]:
                detailed_msg += f"\n\nDropbox Backup Error:\n{results['dropbox']['message']}"
            
            self.update_status(f"❌ {error_msg}")
            QMessageBox.warning(self, "Backup Failed", detailed_msg)
    
    def restore_finished(self, results):
        """Handle restore completion"""
        self.progress_bar.setVisible(False)
        self.hide_loading_overlay()  # Hide loading overlay and enable buttons
        
        if results.get("success"):
            self.update_status("✅ Restore completed successfully")
            QMessageBox.information(self, "Restore Complete", "Database restored successfully!")
        else:
            error_msg = results.get("message", "Restore failed")
            self.update_status(f"❌ {error_msg}")
            QMessageBox.warning(self, "Restore Failed", error_msg)

    def load_settings(self):
        """Load settings from file and database"""
        try:
            # Load non-sensitive settings from file
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    settings = json.load(f)
                    
                self.local_path_input.setText(settings.get("local_path", ""))
                self.max_revisions_spin.setValue(settings.get("max_revisions", 5))
            
            # Load Dropbox token from database
            dropbox_token = get_setting('dropbox_token', '')
            if dropbox_token:
                self.dropbox_token_input.setText(dropbox_token)
                        
        except Exception as e:
            self.update_status(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to file and database"""
        try:
            # Save non-sensitive settings to file
            settings = {
                "local_path": self.local_path_input.text().strip(),
                "max_revisions": self.max_revisions_spin.value()
            }
            
            with open("settings.json", "w") as f:
                json.dump(settings, f, indent=2)
            
            # Save Dropbox token to database
            dropbox_token = self.dropbox_token_input.text().strip()
            if dropbox_token:
                set_setting('dropbox_token', dropbox_token)
                self.update_status("Settings and Dropbox token saved to database")
            else:
                # Clear token if empty
                delete_setting('dropbox_token')
                self.update_status("Settings saved. Dropbox token cleared.")
            
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully!")
            
        except Exception as e:
            self.update_status(f"Error saving settings: {e}")
            QMessageBox.warning(self, "Save Error", f"Failed to save settings: {e}")

# Keep reference alive
open_windows = []

def open_settings_window():
    settings_window = SettingsManager()
    settings_window.show()
    settings_window.raise_()
    open_windows.append(settings_window)
