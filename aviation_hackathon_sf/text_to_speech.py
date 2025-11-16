"""
Text-to-Speech service using ElevenLabs API for aviation checklist announcements.
"""

import os
import requests
import io
from typing import Optional, Union
from pathlib import Path
import pygame
from loguru import logger


class ElevenLabsTTS:
    """
    Text-to-Speech service using ElevenLabs API.
    
    This class provides functionality to convert text to speech using ElevenLabs API,
    specifically designed for aviation checklist announcements and co-pilot assistance.
    """
    
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        """
        Initialize the ElevenLabs TTS service.
        
        Args:
            api_key: ElevenLabs API key. If None, will try to get from environment.
            voice_id: Voice ID to use. If None, uses default voice.
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable or pass api_key parameter.")
        
        # Default voice ID (Rachel - clear, professional voice good for aviation)
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"
        
        # API endpoints
        self.base_url = "https://api.elevenlabs.io/v1"
        self.tts_url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        self.voices_url = f"{self.base_url}/voices"
        
        # Headers for API requests
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
            self.audio_enabled = True
        except Exception as e:
            logger.warning(f"Could not initialize audio playback: {e}")
            self.audio_enabled = False
    
    def get_available_voices(self) -> dict:
        """
        Get list of available voices from ElevenLabs.
        
        Returns:
            Dictionary containing voice information
        """
        try:
            response = requests.get(self.voices_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get voices: {e}")
            return {}
    
    def set_voice(self, voice_id: str):
        """
        Set the voice ID to use for TTS.
        
        Args:
            voice_id: ElevenLabs voice ID
        """
        self.voice_id = voice_id
        self.tts_url = f"{self.base_url}/text-to-speech/{voice_id}"
        logger.info(f"Voice set to: {voice_id}")
    
    def text_to_speech(
        self,
        text: str,
        voice_settings: Optional[dict] = None,
        model_id: str = "eleven_turbo_v2_5"
    ) -> bytes:
        """
        Convert text to speech and return audio data.
        
        Args:
            text: Text to convert to speech
            voice_settings: Voice settings (stability, similarity_boost, style, use_speaker_boost)
            model_id: ElevenLabs model ID to use
            
        Returns:
            Audio data as bytes
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Default voice settings optimized for aviation announcements
        if voice_settings is None:
            voice_settings = {
                "stability": 0.75,      # Higher stability for clear pronunciation
                "similarity_boost": 0.8, # High similarity to maintain voice consistency
                "style": 0.2,           # Lower style for more neutral tone
                "use_speaker_boost": True
            }
        
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings
        }
        
        try:
            response = requests.post(self.tts_url, json=data, headers=self.headers)
            response.raise_for_status()
            
            logger.info(f"Successfully generated speech for text: '{text[:50]}...'")
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"Failed to generate speech: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def save_audio(self, audio_data: bytes, filename: Union[str, Path]) -> str:
        """
        Save audio data to file.
        
        Args:
            audio_data: Audio data as bytes
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        logger.info(f"Audio saved to: {filepath}")
        return str(filepath)
    
    def play_audio(self, audio_data: bytes):
        """
        Play audio data directly.
        
        Args:
            audio_data: Audio data as bytes
        """
        if not self.audio_enabled:
            logger.warning("Audio playback not available")
            return
        
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            
            # Load and play the audio
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            logger.info("Audio playback completed")
            
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
    
    def speak(
        self, 
        text: str, 
        save_to_file: Optional[Union[str, Path]] = None,
        play_immediately: bool = True,
        voice_settings: Optional[dict] = None
    ) -> Optional[str]:
        """
        Convert text to speech and optionally save/play it.
        
        Args:
            text: Text to convert to speech
            save_to_file: Optional filename to save audio
            play_immediately: Whether to play audio immediately
            voice_settings: Optional voice settings override
            
        Returns:
            Path to saved file if save_to_file is provided, None otherwise
        """
        try:
            # Generate speech
            audio_data = self.text_to_speech(text, voice_settings)
            
            # Save to file if requested
            saved_path = None
            if save_to_file:
                saved_path = self.save_audio(audio_data, save_to_file)
            
            # Play immediately if requested
            if play_immediately:
                self.play_audio(audio_data)
            
            return saved_path
            
        except Exception as e:
            logger.error(f"Failed to speak text: {e}")
            raise
    
    def speak_checklist_item(
        self, 
        item_name: str, 
        status: str = "check",
        save_audio: bool = False,
        audio_dir: Optional[Union[str, Path]] = None
    ) -> Optional[str]:
        """
        Speak a checklist item with aviation-appropriate formatting.
        
        Args:
            item_name: Name of the checklist item
            status: Status of the item ("check", "complete", "warning", "failed")
            save_audio: Whether to save audio file
            audio_dir: Directory to save audio files
            
        Returns:
            Path to saved audio file if save_audio is True
        """
        # Format text for aviation context
        status_phrases = {
            "check": f"{item_name}, check.",
            "complete": f"{item_name}, complete.",
            "warning": f"Warning: {item_name} requires attention.",
            "failed": f"Alert: {item_name} check failed.",
            "caution": f"Caution: {item_name}."
        }
        
        text = status_phrases.get(status.lower(), f"{item_name}, {status}.")
        
        # Determine save path
        save_path = None
        if save_audio:
            if audio_dir:
                audio_dir = Path(audio_dir)
                audio_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{item_name.lower().replace(' ', '_')}_{status}.mp3"
                save_path = audio_dir / filename
            else:
                save_path = f"{item_name.lower().replace(' ', '_')}_{status}.mp3"
        
        return self.speak(
            text=text,
            save_to_file=save_path,
            play_immediately=True
        )


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    try:
        # Initialize TTS service
        tts = ElevenLabsTTS()
        
        # Test basic functionality
        print("Testing ElevenLabs TTS...")
        
        # Speak a simple message
        tts.speak("Aviation checklist system initialized. Ready for pre-flight checks.")
        
        # Test checklist items
        checklist_items = [
            ("Doors", "check"),
            ("Fuel Quantity", "complete"),
            ("Engine Parameters", "warning")
        ]
        
        for item, status in checklist_items:
            tts.speak_checklist_item(item, status, save_audio=True, audio_dir="audio_output")
        
        print("TTS testing completed successfully!")
        
    except Exception as e:
        print(f"Error testing TTS: {e}")
        print("Make sure to set ELEVENLABS_API_KEY environment variable")