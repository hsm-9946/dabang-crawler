#!/usr/bin/env python3
"""
다방 크롤러 아이콘 생성 스크립트
PIL을 사용하여 간단한 아이콘을 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """다방 크롤러 아이콘 생성"""
    
    # assets 디렉토리 생성
    os.makedirs("assets", exist_ok=True)
    
    # 256x256 크기의 아이콘 생성
    size = 256
    icon = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(icon)
    
    # 배경 원 그리기
    draw.ellipse([20, 20, size-20, size-20], fill=(52, 152, 219, 255), outline=(41, 128, 185, 255), width=5)
    
    # 집 모양 그리기
    house_color = (255, 255, 255, 255)
    # 집 몸체
    draw.rectangle([80, 120, 176, 200], fill=house_color, outline=(200, 200, 200, 255), width=2)
    # 지붕
    draw.polygon([(60, 120), (128, 80), (196, 120)], fill=house_color, outline=(200, 200, 200, 255), width=2)
    # 문
    draw.rectangle([110, 160, 130, 200], fill=(139, 69, 19, 255), outline=(101, 67, 33, 255), width=1)
    # 창문
    draw.rectangle([90, 130, 110, 150], fill=(135, 206, 235, 255), outline=(200, 200, 200, 255), width=1)
    draw.rectangle([146, 130, 166, 150], fill=(135, 206, 235, 255), outline=(200, 200, 200, 255), width=1)
    
    # 텍스트 추가
    try:
        # 기본 폰트 사용
        font = ImageFont.load_default()
        text = "다방"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 텍스트 위치 계산 (아이콘 하단)
        text_x = (size - text_width) // 2
        text_y = size - 60
        
        # 텍스트 배경
        draw.rectangle([text_x-10, text_y-5, text_x+text_width+10, text_y+text_height+5], 
                      fill=(52, 152, 219, 200), outline=(41, 128, 185, 255), width=2)
        
        # 텍스트 그리기
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
        
    except Exception as e:
        print(f"폰트 로드 실패: {e}")
        # 폰트 없이 간단한 텍스트
        draw.text((100, 220), "다방", fill=(255, 255, 255, 255))
    
    # 다양한 크기로 저장
    sizes = [16, 32, 48, 64, 128, 256]
    icons = []
    
    for s in sizes:
        resized = icon.resize((s, s), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # ICO 파일로 저장
    icon.save("assets/icon.ico", format='ICO', sizes=[(s, s) for s in sizes])
    print("아이콘 생성 완료: assets/icon.ico")
    
    # PNG 파일로도 저장 (미리보기용)
    icon.save("assets/icon.png", format='PNG')
    print("PNG 아이콘 생성 완료: assets/icon.png")
    
    return True

if __name__ == "__main__":
    try:
        create_icon()
        print("✅ 아이콘 생성 성공!")
    except Exception as e:
        print(f"❌ 아이콘 생성 실패: {e}")
        print("PIL 설치가 필요합니다: pip install pillow")
