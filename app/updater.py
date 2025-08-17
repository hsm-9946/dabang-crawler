#!/usr/bin/env python3
"""
자동 업데이트 체크 모듈
GitHub Releases API를 사용하여 최신 버전을 확인합니다.
"""

import requests
import json
import re
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger

class Updater:
    """자동 업데이트 체크 클래스"""
    
    def __init__(self, repo_owner: str = "hsm-9946", repo_name: str = "dabang-crawler"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        self.current_version = "1.0.0"  # 현재 버전
        
    def get_latest_version(self) -> Optional[str]:
        """최신 버전 정보 가져오기"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            latest_version = data.get('tag_name', '')
            
            # v1.0.0 형식에서 숫자만 추출
            if latest_version.startswith('v'):
                latest_version = latest_version[1:]
            
            return latest_version
            
        except requests.RequestException as e:
            logger.error(f"업데이트 체크 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"업데이트 정보 파싱 실패: {e}")
            return None
    
    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """업데이트 확인"""
        latest_version = self.get_latest_version()
        
        if not latest_version:
            return False, None, None
        
        # 버전 비교
        has_update = self._compare_versions(self.current_version, latest_version)
        
        if has_update:
            download_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/releases/latest"
            return True, latest_version, download_url
        
        return False, None, None
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """버전 비교"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            # 최대 3자리까지 비교
            for i in range(max(len(current_parts), len(latest_parts))):
                current_part = current_parts[i] if i < len(current_parts) else 0
                latest_part = latest_parts[i] if i < len(latest_parts) else 0
                
                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False
            
            return False  # 동일한 버전
            
        except (ValueError, IndexError):
            logger.error("버전 비교 실패")
            return False
    
    def get_release_notes(self, version: str) -> Optional[str]:
        """릴리즈 노트 가져오기"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('body', '')
            
        except Exception as e:
            logger.error(f"릴리즈 노트 가져오기 실패: {e}")
            return None

def check_updates() -> Tuple[bool, Optional[str], Optional[str]]:
    """업데이트 체크 함수 (간편 사용)"""
    updater = Updater()
    return updater.check_for_updates()

if __name__ == "__main__":
    # 테스트
    updater = Updater()
    has_update, latest_version, download_url = updater.check_for_updates()
    
    if has_update:
        print(f"새로운 버전이 있습니다: {latest_version}")
        print(f"다운로드: {download_url}")
    else:
        print("최신 버전을 사용 중입니다.")
