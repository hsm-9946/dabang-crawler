#!/usr/bin/env node

const { exec } = require('child_process');
const path = require('path');

console.log('🔄 페이지네이션 기능 테스트 시작...\n');

// 테스트 실행
const testCommand = `npx tsx scripts/dabang_scrape.ts --type "원룸" --region "부산 기장" --limit 5 --skip-detail false`;

console.log(`실행 명령어: ${testCommand}\n`);

const child = exec(testCommand, { 
  cwd: process.cwd(),
  maxBuffer: 1024 * 1024 * 10 // 10MB
});

child.stdout.on('data', (data) => {
  console.log(data.toString());
});

child.stderr.on('data', (data) => {
  console.error(data.toString());
});

child.on('close', (code) => {
  console.log(`\n🎯 테스트 완료 (종료 코드: ${code})`);
  
  if (code === 0) {
    console.log('✅ 페이지네이션 테스트 성공!');
  } else {
    console.log('❌ 페이지네이션 테스트 실패!');
  }
});

child.on('error', (error) => {
  console.error('❌ 테스트 실행 중 오류:', error);
});
