const { spawn } = require('child_process');

const propertyTypes = ['원룸', '아파트', '주택/빌라', '오피스텔'];

console.log('🔄 모든 매물 유형 크롤링 테스트 시작...\n');

async function testPropertyType(type) {
  console.log(`\n🏠 ${type} 크롤링 테스트 시작...`);
  
  return new Promise((resolve) => {
    const child = spawn('npx', ['tsx', 'scripts/dabang_scrape.ts', '--type', type, '--region', '부산 기장', '--limit', '2', '--skip-detail', 'false'], {
      stdio: 'inherit',
      shell: true
    });

    child.on('close', (code) => {
      console.log(`\n✅ ${type} 테스트 완료 (종료 코드: ${code})`);
      resolve(code);
    });

    child.on('error', (error) => {
      console.error(`❌ ${type} 테스트 실행 중 오류:`, error);
      resolve(1);
    });
  });
}

async function runAllTests() {
  for (const type of propertyTypes) {
    await testPropertyType(type);
    // 테스트 간 간격
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('\n🎉 모든 매물 유형 테스트 완료!');
}

runAllTests();
