// Astro Pagefind 集成配置
export default function pagefindIntegration() {
	return {
		name: "pagefind-integration",
		hooks: {
			"astro:build:done": async ({ dir }) => {
				console.log("Building Pagefind search index...");

				try {
					const { execSync } = await import("child_process");

					// 执行 pagefind 索引构建
					execSync("npx pagefind --site dist", {
						stdio: "inherit",
						cwd: process.cwd(),
						shell: true, // 使用shell模式
					});

					console.log("Pagefind search index built successfully!");
				} catch (error) {
					console.error("Failed to build Pagefind index:", error);
					// 不中断构建过程，只是警告
					console.warn("Search functionality may not work properly");
				}
			},
		},
	};
}
