const { spawn } = require('child_process');

console.log('🔄 아파트 크롤링 기능 테스트 시작...\n');

// 테스트 실행
const testCommand = `npx tsx scripts/dabang_scrape.ts --type "아파트" --region "부산 기장" --limit 3 --skip-detail false`;

console.log(`실행 명령어: ${testCommand}\n`);

// 프로세스 실행
const child = spawn('npx', ['tsx', 'scripts/dabang_scrape.ts', '--type', '아파트', '--region', '부산 기장', '--limit', '3', '--skip-detail', 'false'], {
  stdio: 'inherit',
  shell: true
});

// 프로세스 종료 처리
child.on('close', (code) => {
  console.log(`\n✅ 테스트 완료 (종료 코드: ${code})`);
});

child.on('error', (error) => {
  console.error('❌ 테스트 실행 중 오류:', error);
});
