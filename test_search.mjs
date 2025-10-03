import { execSync } from 'child_process';

// 测试不同的搜索方式
const testKeyword = '100万';

console.log('测试搜索关键词:', testKeyword);
console.log('===================');

// 测试1: 直接搜索
try {
  console.log('1. 直接搜索:', testKeyword);
  const directResult = execSync(`npx pagefind --site dist --search "${testKeyword}"`, { encoding: 'utf8' });
  console.log('结果:', directResult);
} catch (error) {
  console.log('直接搜索失败:', error.message);
}

// 测试2: 严格匹配搜索
try {
  console.log('\n2. 严格匹配搜索:', `"${testKeyword}"`);
  const exactResult = execSync(`npx pagefind --site dist --search "\\"${testKeyword}\\""`, { encoding: 'utf8' });
  console.log('结果:', exactResult);
} catch (error) {
  console.log('严格匹配搜索失败:', error.message);
}

// 测试3: 查看索引统计
try {
  console.log('\n3. 索引统计:');
  const stats = execSync(`npx pagefind --site dist --stats`, { encoding: 'utf8' });
  console.log('统计:', stats);
} catch (error) {
  console.log('获取统计失败:', error.message);
}