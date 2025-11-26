"""This module handles the Garmin connectivity."""

import io
import logging
import os

import garth
# Temporary fix until Garth project merges https://github.com/matin/garth/issues/73
garth.http.USER_AGENT = {"User-Agent": ("GCM-iOS-5.7.2.1")}

log = logging.getLogger("garmin")

HOME = os.getenv("HOME", ".")
GARMIN_SESSION = os.path.abspath(os.path.expanduser(os.getenv('GARMIN_SESSION', os.path.join(HOME, ".garmin_session"))))


class LoginFailed(Exception):
    """Raised when login fails."""


class APIException(Exception):
    """Raised for API exceptions."""


class GarminConnect:
    """Main GarminConnect class."""

    def __init__(self) -> None:
        self.client = garth.Client()

    def login(self, email=None, password=None):
        """Login to Garmin Connect with session persistence and MFA support."""
        log.debug("Attempting Garmin login")
        
        if GarminConnect.invalid_garmin_session_config():
            raise APIException("GARMIN_SESSION environment variable cannot be empty")
        
        if GarminConnect.garmin_session_is_directory():
            raise APIException(
                f"GARMIN_SESSION points to a directory ({GARMIN_SESSION}) but must point to a file path. "
                f"For Docker usage, ensure you mount the .garmin_session FILE, not the containing directory."
            )
        
        if os.path.exists(GARMIN_SESSION):
            try:
                log.debug("Loading existing Garmin session")
                self.client.load(GARMIN_SESSION)
                if self.looks_like_valid_session():
                    log.info(f"Successfully loaded Garmin session for user: {self.client.username}")
                    return
                else:
                    log.warning("Session file exists but appears invalid or expired")
            except Exception as ex:
                log.warning(f"Failed to load Garmin session: {ex}")
        
        # Fallback to credential authentication
        if not email or not password:
            raise APIException(
                "No valid session found and no credentials provided. "
                "For MFA accounts:"
                "1) Authenticate once using Garmin Connect mobile app or web interface, "
                "2) Locate the .garmin_session file in your home directory, "
                "3) Copy this file to the location specified by GARMIN_SESSION environment variable."
            )
        
        # Check write permissions BEFORE attempting authentication
        session_dir = os.path.dirname(GARMIN_SESSION)
        if session_dir and not os.access(session_dir, os.W_OK):
            log.warning(f"Cannot write to session directory: {session_dir}")
        
        try:
            log.info("Attempting Garmin authentication with credentials")
            self.client.login(email, password)
            log.info("Garmin authentication successful")
            
        except Exception as ex:
            raise APIException(
                f"Authentication failure: {ex}. "
                f"For MFA accounts, credential-based login may not work. "
                f"Use the session file method described in the error message above."
            )
        
        # Save session separately to handle dump failures distinctly
        try:
            # Ensure parent directory exists before dumping session
            if session_dir:
                os.makedirs(session_dir, exist_ok=True)
                log.debug("Session directory created/verified")
            
            self.client.dump(GARMIN_SESSION)
            log.info(f"Successfully saved Garmin session to {session_dir}")
            
        except Exception as ex:
            raise APIException(
                f"Session save failed: {ex}. Authentication succeeded but session could not be persisted. "
                f"Check GARMIN_SESSION path, permissions, and available disk space."
            )

    def looks_like_valid_session(self) -> bool:
        return hasattr(self.client, "username") and self.client.username

    @staticmethod
    def garmin_session_is_directory() -> bool:
        return os.path.isdir(GARMIN_SESSION)

    @staticmethod
    def invalid_garmin_session_config() -> bool:
        return not GARMIN_SESSION.strip()

    def upload_file(self, ffile):
        """Upload fit file to Garmin Connect."""
        fit_file = io.BytesIO(ffile.getvalue())
        fit_file.name = "withings.fit"
        self.client.upload(fit_file)
        return True
