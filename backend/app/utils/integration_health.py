"""
Integration health checker for PMOVES services.

This module provides async health checks for external service dependencies
used in standalone mode (TensorZero, NATS, GPU Orchestrator).
"""

import asyncio
import os
from typing import Dict, Optional
import logging

import aiohttp
import nats

logger = logging.getLogger(__name__)


class IntegrationHealth:
    """Integration health checker for PMOVES services."""

    def __init__(self):
        """Initialize health checker with configuration from environment."""
        self.tensorzero_url = os.getenv(
            'TENSORZERO_BASE_URL',
            'http://tensorzero-gateway:3030'
        ).rstrip('/')
        self.nats_url = os.getenv('NATS_URL', 'nats://nats:pmoves@nats:4222')
        self.gpu_orchestrator_url = os.getenv('GPU_ORCHESTRATOR_URL')

    async def check_tensorzero(self, timeout: float = 2.0) -> bool:
        """
        Check if TensorZero Gateway is reachable.

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if TensorZero is healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.tensorzero_url}/health",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    is_healthy = resp.status == 200
                    if is_healthy:
                        logger.debug(f"TensorZero health check passed: {self.tensorzero_url}")
                    else:
                        logger.warning(f"TensorZero returned status {resp.status}")
                    return is_healthy
        except asyncio.TimeoutError:
            logger.warning(f"TensorZero health check timed out: {self.tensorzero_url}")
            return False
        except Exception as e:
            logger.warning(f"TensorZero health check failed: {e}")
            return False

    async def check_nats(self, timeout: float = 2.0) -> bool:
        """
        Check if NATS is reachable.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if NATS is reachable, False otherwise
        """
        try:
            nc = await nats.connect(
                self.nats_url,
                timeout=timeout
            )
            await nc.flush()
            await nc.close()
            logger.debug(f"NATS health check passed: {self.nats_url}")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"NATS health check timed out: {self.nats_url}")
            return False
        except Exception as e:
            logger.warning(f"NATS health check failed: {e}")
            return False

    async def check_gpu_orchestrator(self, timeout: float = 2.0) -> bool:
        """
        Check if GPU Orchestrator is reachable (optional).

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if GPU Orchestrator is healthy, False if not or not configured
        """
        if not self.gpu_orchestrator_url:
            logger.debug("GPU Orchestrator not configured, skipping check")
            return False  # Not configured

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.gpu_orchestrator_url}/healthz",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    is_healthy = resp.status == 200
                    if is_healthy:
                        logger.debug(f"GPU Orchestrator health check passed: {self.gpu_orchestrator_url}")
                    else:
                        logger.warning(f"GPU Orchestrator returned status {resp.status}")
                    return is_healthy
        except asyncio.TimeoutError:
            logger.warning(f"GPU Orchestrator health check timed out: {self.gpu_orchestrator_url}")
            return False
        except Exception as e:
            logger.warning(f"GPU Orchestrator health check failed: {e}")
            return False

    async def get_status(self) -> Dict[str, Dict]:
        """
        Get all integration health statuses.

        Returns:
            Dict mapping integration names to their health status and URLs
        """
        results = await asyncio.gather(
            self.check_tensorzero(),
            self.check_nats(),
            self.check_gpu_orchestrator(),
            return_exceptions=True
        )

        return {
            "tensorzero": {
                "healthy": results[0] if not isinstance(results[0], Exception) else False,
                "url": self.tensorzero_url
            },
            "nats": {
                "healthy": results[1] if not isinstance(results[1], Exception) else False,
                "url": self.nats_url
            },
            "gpu_orchestrator": {
                "healthy": results[2] if not isinstance(results[2], Exception) else False,
                "url": self.gpu_orchestrator_url
            }
        }
