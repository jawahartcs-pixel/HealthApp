import sqlite3
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import streamlit as st

class AuthSystem:
    def __init__(self, db_path: str = "blood_test_results.db"):
        """Initialize authentication system with database connection."""
        self.db_path = db_path
        self.init_auth_database()
    
    def init_auth_database(self):
        """Create authentication tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                failed_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        ''')
        
        # Create password reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Update existing tables to include user_id (if not already present)
        try:
            cursor.execute('ALTER TABLE patients ADD COLUMN user_id INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE test_results ADD COLUMN user_id INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt."""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _generate_salt(self) -> str:
        """Generate random salt for password hashing."""
        return secrets.token_hex(16)
    
    def _generate_token(self) -> str:
        """Generate secure token for password reset."""
        return secrets.token_urlsafe(32)
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user."""
        try:
            # Validate input
            if not username or not email or not password:
                return {"success": False, "message": "All fields are required"}
            
            if len(password) < 8:
                return {"success": False, "message": "Password must be at least 8 characters long"}
            
            # Check if username or email already exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                conn.close()
                return {"success": False, "message": "Username or email already exists"}
            
            # Create user
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, salt))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "User registered successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Registration failed: {str(e)}"}
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user login."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, is_active, 
                       failed_attempts, locked_until
                FROM users WHERE username = ?
            ''', (username,))
            
            user_data = cursor.fetchone()
            if not user_data:
                conn.close()
                return {"success": False, "message": "Invalid username or password"}
            
            user_id, username, email, stored_hash, salt, is_active, failed_attempts, locked_until = user_data
            
            # Check if account is locked
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    conn.close()
                    return {"success": False, "message": f"Account locked until {lock_time.strftime('%Y-%m-%d %H:%M:%S')}"}
            
            # Check if account is active
            if not is_active:
                conn.close()
                return {"success": False, "message": "Account is deactivated"}
            
            # Verify password
            password_hash = self._hash_password(password, salt)
            if password_hash != stored_hash:
                # Increment failed attempts
                failed_attempts += 1
                if failed_attempts >= 5:
                    # Lock account for 30 minutes
                    locked_until = datetime.now() + timedelta(minutes=30)
                    cursor.execute('''
                        UPDATE users SET failed_attempts = ?, locked_until = ?
                        WHERE id = ?
                    ''', (failed_attempts, locked_until.isoformat(), user_id))
                else:
                    cursor.execute('''
                        UPDATE users SET failed_attempts = ? WHERE id = ?
                    ''', (failed_attempts, user_id))
                
                conn.commit()
                conn.close()
                return {"success": False, "message": "Invalid username or password"}
            
            # Successful login - reset failed attempts and update last login
            cursor.execute('''
                UPDATE users SET failed_attempts = 0, locked_until = NULL, 
                                last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "Login successful",
                "user_id": user_id,
                "username": username,
                "email": email
            }
            
        except Exception as e:
            return {"success": False, "message": f"Authentication failed: {str(e)}"}
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password."""
        try:
            if len(new_password) < 8:
                return {"success": False, "message": "New password must be at least 8 characters long"}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current password hash and salt
            cursor.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                conn.close()
                return {"success": False, "message": "User not found"}
            
            stored_hash, salt = user_data
            
            # Verify current password
            current_hash = self._hash_password(current_password, salt)
            if current_hash != stored_hash:
                conn.close()
                return {"success": False, "message": "Current password is incorrect"}
            
            # Generate new salt and hash for new password
            new_salt = self._generate_salt()
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update password
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ?
                WHERE id = ?
            ''', (new_hash, new_salt, user_id))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Password changed successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Password change failed: {str(e)}"}
    
    def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """Initiate password reset process."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user_data = cursor.fetchone()
            
            if not user_data:
                conn.close()
                # Don't reveal if email exists or not for security
                return {"success": True, "message": "If email exists, reset instructions have been sent"}
            
            user_id = user_data[0]
            
            # Generate reset token
            token = self._generate_token()
            expires_at = datetime.now() + timedelta(hours=1)
            
            # Store token
            cursor.execute('''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, token, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            # In a real application, you would send this token via email
            # For now, we'll return it in the response (NOT recommended for production)
            return {
                "success": True,
                "message": "Password reset token generated",
                "token": token  # Remove this in production
            }
            
        except Exception as e:
            return {"success": False, "message": f"Password reset failed: {str(e)}"}
    
    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Reset password using token."""
        try:
            if len(new_password) < 8:
                return {"success": False, "message": "New password must be at least 8 characters long"}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify token
            cursor.execute('''
                SELECT user_id, expires_at FROM password_reset_tokens
                WHERE token = ? AND used = 0
            ''', (token,))
            
            token_data = cursor.fetchone()
            if not token_data:
                conn.close()
                return {"success": False, "message": "Invalid or expired token"}
            
            user_id, expires_at = token_data
            
            # Check if token is expired
            if datetime.now() > datetime.fromisoformat(expires_at):
                conn.close()
                return {"success": False, "message": "Token has expired"}
            
            # Generate new salt and hash
            new_salt = self._generate_salt()
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update password
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ?
                WHERE id = ?
            ''', (new_hash, new_salt, user_id))
            
            # Mark token as used
            cursor.execute('''
                UPDATE password_reset_tokens SET used = 1
                WHERE token = ?
            ''', (token,))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Password reset successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Password reset failed: {str(e)}"}
    
    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data:
                return {
                    "id": user_data[0],
                    "username": user_data[1],
                    "email": user_data[2],
                    "created_at": user_data[3],
                    "last_login": user_data[4]
                }
            
            return None
            
        except Exception as e:
            return None
    
    def update_user_info(self, user_id: int, username: str = None, email: str = None) -> Dict[str, Any]:
        """Update user information."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if username:
                # Check if username already exists
                cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
                if cursor.fetchone():
                    conn.close()
                    return {"success": False, "message": "Username already exists"}
                updates.append("username = ?")
                params.append(username)
            
            if email:
                # Check if email already exists
                cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
                if cursor.fetchone():
                    conn.close()
                    return {"success": False, "message": "Email already exists"}
                updates.append("email = ?")
                params.append(email)
            
            if not updates:
                conn.close()
                return {"success": False, "message": "No updates provided"}
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "User information updated successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Update failed: {str(e)}"}
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return 'user_id' in st.session_state and st.session_state.user_id is not None
    
    def get_current_user_id(self) -> Optional[int]:
        """Get current logged in user ID."""
        return st.session_state.get('user_id')
    
    def logout(self):
        """Logout current user."""
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()