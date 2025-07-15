import streamlit as st
from auth_system import AuthSystem
from typing import Optional

class AuthUI:
    def __init__(self, auth_system: AuthSystem):
        """Initialize authentication UI with auth system."""
        self.auth_system = auth_system
    
    def login_page(self):
        """Display login page."""
        st.title("🔐 Login")
        
        # Create tabs for different auth actions
        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
        
        with tab1:
            self._login_form()
        
        with tab2:
            self._register_form()
        
        with tab3:
            self._reset_password_form()
    
    def _login_form(self):
        """Display login form."""
        st.subheader("Sign In")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_submitted = st.form_submit_button("Login", type="primary")
            with col2:
                if st.form_submit_button("Demo Mode"):
                    # Set demo mode for testing without authentication
                    st.session_state.demo_mode = True
                    st.session_state.user_id = None
                    st.session_state.username = "Demo User"
                    st.success("Demo mode activated! You can test the app without authentication.")
                    st.rerun()
        
        if login_submitted:
            if username and password:
                result = self.auth_system.authenticate_user(username, password)
                
                if result["success"]:
                    st.session_state.user_id = result["user_id"]
                    st.session_state.username = result["username"]
                    st.session_state.email = result["email"]
                    st.session_state.demo_mode = False
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.error("Please enter both username and password")
    
    def _register_form(self):
        """Display registration form."""
        st.subheader("Create Account")
        
        with st.form("register_form"):
            username = st.text_input("Username", placeholder="Choose a username")
            email = st.text_input("Email", placeholder="Enter your email address")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            register_submitted = st.form_submit_button("Register", type="primary")
        
        if register_submitted:
            if username and email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    result = self.auth_system.register_user(username, email, password)
                    
                    if result["success"]:
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error(result["message"])
            else:
                st.error("Please fill in all fields")
    
    def _reset_password_form(self):
        """Display password reset form."""
        st.subheader("Reset Password")
        
        if 'reset_token' not in st.session_state:
            st.session_state.reset_token = None
        
        if not st.session_state.reset_token:
            # Step 1: Request reset token
            with st.form("reset_request_form"):
                email = st.text_input("Email", placeholder="Enter your email address")
                reset_submitted = st.form_submit_button("Send Reset Link", type="primary")
            
            if reset_submitted:
                if email:
                    result = self.auth_system.initiate_password_reset(email)
                    
                    if result["success"]:
                        st.success("Reset instructions sent!")
                        # In a real app, this would be sent via email
                        # For demo purposes, we'll show the token
                        if "token" in result:
                            st.session_state.reset_token = result["token"]
                            st.info(f"Demo: Your reset token is: {result['token']}")
                            st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.error("Please enter your email address")
        else:
            # Step 2: Reset password with token
            with st.form("reset_password_form"):
                token = st.text_input("Reset Token", value=st.session_state.reset_token)
                new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password")
                
                col1, col2 = st.columns(2)
                with col1:
                    reset_submitted = st.form_submit_button("Reset Password", type="primary")
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.reset_token = None
                        st.rerun()
            
            if reset_submitted:
                if token and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        result = self.auth_system.reset_password(token, new_password)
                        
                        if result["success"]:
                            st.success("Password reset successfully! Please login.")
                            st.session_state.reset_token = None
                        else:
                            st.error(result["message"])
                else:
                    st.error("Please fill in all fields")
    
    def user_profile_page(self):
        """Display user profile management page."""
        st.title("👤 User Profile")
        
        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Please login to view profile")
            return
        
        user_info = self.auth_system.get_user_info(user_id)
        
        if not user_info:
            st.error("User information not found")
            return
        
        # Display current user info
        st.subheader("Current Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Username:** {user_info['username']}")
            st.info(f"**Email:** {user_info['email']}")
        
        with col2:
            st.info(f"**Member Since:** {user_info['created_at']}")
            if user_info['last_login']:
                st.info(f"**Last Login:** {user_info['last_login']}")
        
        st.divider()
        
        # Update profile form
        st.subheader("Update Profile")
        with st.form("update_profile_form"):
            new_username = st.text_input("New Username", value=user_info['username'])
            new_email = st.text_input("New Email", value=user_info['email'])
            
            update_submitted = st.form_submit_button("Update Profile", type="primary")
        
        if update_submitted:
            changes = {}
            if new_username != user_info['username']:
                changes['username'] = new_username
            if new_email != user_info['email']:
                changes['email'] = new_email
            
            if changes:
                result = self.auth_system.update_user_info(user_id, **changes)
                
                if result["success"]:
                    st.success("Profile updated successfully!")
                    # Update session state if username changed
                    if 'username' in changes:
                        st.session_state.username = new_username
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.info("No changes made")
        
        st.divider()
        
        # Change password form
        st.subheader("Change Password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_new_password = st.text_input("Confirm New Password", type="password")
            
            change_password_submitted = st.form_submit_button("Change Password", type="primary")
        
        if change_password_submitted:
            if current_password and new_password and confirm_new_password:
                if new_password != confirm_new_password:
                    st.error("New passwords do not match")
                else:
                    result = self.auth_system.change_password(user_id, current_password, new_password)
                    
                    if result["success"]:
                        st.success("Password changed successfully!")
                    else:
                        st.error(result["message"])
            else:
                st.error("Please fill in all fields")
        
        st.divider()
        
        # Logout button
        if st.button("Logout", type="secondary"):
            self.auth_system.logout()
    
    def sidebar_user_info(self):
        """Display user info in sidebar."""
        if st.session_state.get('demo_mode'):
            st.sidebar.info("🔓 Demo Mode Active")
            if st.sidebar.button("Exit Demo Mode"):
                st.session_state.demo_mode = False
                st.rerun()
        elif st.session_state.get('user_id'):
            st.sidebar.success(f"👤 Welcome, {st.session_state.username}!")
            
            if st.sidebar.button("User Profile"):
                st.session_state.page = "Profile"
                st.rerun()
            
            if st.sidebar.button("Logout"):
                self.auth_system.logout()
        else:
            st.sidebar.warning("Please login to continue")
    
    def check_authentication(self) -> bool:
        """Check if user is authenticated or in demo mode."""
        return (st.session_state.get('user_id') is not None or 
                st.session_state.get('demo_mode', False))