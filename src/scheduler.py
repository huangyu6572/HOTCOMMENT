"""
定时调度器

基于 APScheduler，按配置 cron 表达式定时触发全流程
"""

from pathlib import Path
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class Scheduler:
    """定时调度器"""

    def __init__(self, orchestrator, settings: dict):
        self.orchestrator = orchestrator
        self.settings = settings
        self._scheduler = AsyncIOScheduler()

    def start(self):
        """启动调度器"""
        schedule_config = self.settings.get("schedule", {})
        if not schedule_config.get("enabled", False):
            logger.info("定时调度未启用")
            return

        cron_expr = schedule_config.get("cron", "0 8,14,20 * * *")
        logger.info(f"启动定时调度: {cron_expr}")

        self._scheduler.add_job(
            self._run_job,
            trigger=CronTrigger.from_crontab(cron_expr),
            id="hotcommenthub_main",
            name="全流程执行",
            replace_existing=True,
        )

        # 每日报告生成（每天 23:00）
        self._scheduler.add_job(
            self._generate_report_job,
            trigger=CronTrigger.from_crontab("0 23 * * *"),
            id="daily_report",
            name="每日报告",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("调度器已启动，等待触发...")

    async def _run_job(self):
        """定时任务：执行全流程"""
        logger.info("⏰ 定时触发全流程执行")
        try:
            await self.orchestrator.run()
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")

    async def _generate_report_job(self):
        """定时任务：生成每日报告"""
        try:
            from .reports.daily_digest import generate_daily_report
            generate_daily_report(self.orchestrator.data_dir)
        except Exception as e:
            logger.error(f"每日报告生成失败: {e}")

    def run_once(self):
        """执行一次全流程（不启动定时器）"""
        import asyncio
        asyncio.run(self.orchestrator.run())

    def stop(self):
        """停止调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("调度器已停止")
