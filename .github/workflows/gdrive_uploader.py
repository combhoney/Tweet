# -*- coding: utf-8 -*-
import os, subprocess
from config import GDRIVE_PARENT_FOLDER_ID

def upload_to_google_drive(video_path, thumbnail_path, title):
    """
    Rclone ব্যবহার করে ভিডিও ও থাম্বনেইল গুগল ড্রাইভের ফোল্ডার বা রুটে আপলোড করে
    """
    print("\n" + "="*65)
    print("☁️ [G-DRIVE UPLOADER] Starting Rclone Upload to Google Drive")
    print("="*65)

    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return False

    # ড্রাইভ রুট নাকি স্পেসিফিক ফোল্ডার
    rclone_cmd_base = ["rclone", "copy"]
    
    if GDRIVE_PARENT_FOLDER_ID:
        target_dest = "gdrive:"
        extra_flags = ["--drive-root-folder-id", GDRIVE_PARENT_FOLDER_ID, "--fast-list"]
        print(f"📁 Target Google Drive Folder ID: {GDRIVE_PARENT_FOLDER_ID}")
    else:
        target_dest = "gdrive:"
        extra_flags = ["--fast-list"]
        print("📁 Target Google Drive: ROOT DIRECTORY")

    try:
        # ১. ভিডিও ফাইল আপলোড
        print(f"📤 Uploading Video: '{os.path.basename(video_path)}'...")
        cmd_vid = rclone_cmd_base + [video_path, target_dest] + extra_flags
        res_vid = subprocess.run(cmd_vid, capture_output=True, text=True)
        if res_vid.returncode != 0:
            print(f"❌ Video upload failed! Rclone error: {res_vid.stderr}")
            return False

        # ২. থাম্বনেইল ফাইল আপলোড
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"📤 Uploading Thumbnail: '{os.path.basename(thumbnail_path)}'...")
            cmd_thmb = rclone_cmd_base + [thumbnail_path, target_dest] + extra_flags
            subprocess.run(cmd_thmb, capture_output=True, text=True)

        print(f"🎉 [SUCCESS] Video & Thumbnail successfully stored in Google Drive!")
        return True

    except Exception as e:
        print(f"❌ Rclone execution failed: {e}")
        return False
