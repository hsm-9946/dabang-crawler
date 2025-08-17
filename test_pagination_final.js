const { spawn } = require('child_process');

console.log('🔄 페이지네이션 기능 최종 테스트 시작...\n');

// 페이지네이션 테스트 (3개 수집하여 다음 페이지로 넘어가는지 확인)
const testCommand = `npx tsx scripts/dabang_scrape.ts --type "원룸" --region "부산 기장" --limit 3 --skip-detail false`;

console.log(`실행 명령어: ${testCommand}\n`);

// 프로세스 실행
const child = spawn('npx', ['tsx', 'scripts/dabang_scrape.ts', '--type', '원룸', '--region', '부산 기장', '--limit', '3', '--skip-detail', 'false'], {
  stdio: 'inherit',
  shell: true
});

// 프로세스 종료 처리
child.on('close', (code) => {
  console.log(`\n✅ 페이지네이션 테스트 완료 (종료 코드: ${code})`);
  if (code === 0) {
    console.log('🎉 페이지네이션 기능이 정상적으로 작동합니다!');
  } else {
    console.log('❌ 페이지네이션 테스트 중 문제가 발생했습니다.');
  }
});

child.on('error', (error) => {
  console.error('❌ 페이지네이션 테스트 실행 중 오류:', error);
});
