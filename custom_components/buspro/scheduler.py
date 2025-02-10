# Scheduler for periodic reading of Buspro entities

import asyncio
import logging
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, hass):
        _LOGGER.debug("Initializing Scheduler")
        self.hass = hass
        self.entities_to_read = {}
        self.default_read_interval = timedelta(seconds=10)

    async def add_entity(self, entity):
        entity_id = entity.entity_id
        scan_interval = entity.scan_interval
        _LOGGER.debug(f"Adding entity {entity_id} to scheduler scan_interval {scan_interval}")

        if scan_interval is None or scan_interval == 0:
            scan_interval = timedelta(seconds=0)
        else:
            try:
                scan_interval = timedelta(seconds=int(scan_interval))
            except ValueError:
                _LOGGER.error(f"Invalid scan_interval for entity {entity_id}: {scan_interval}")
                scan_interval = self.default_read_interval

        next_read_time = datetime.now() + scan_interval
        self.entities_to_read[entity_id] = {
            'last_read': datetime.min,
            'scan_interval': scan_interval,
            'next_read_time': next_read_time
        }

    def _get_sorted_entities_with_interval(self, now):
        entities_with_interval = [
            (entity_id, info) for entity_id, info in self.entities_to_read.items()
            if info['scan_interval'] > timedelta(seconds=0) and now >= info['next_read_time']
        ]
        return sorted(entities_with_interval, key=lambda item: item[1]['next_read_time'])

    def _get_sorted_entities_without_interval(self, now):
        entities_without_interval = [
            (entity_id, info) for entity_id, info in self.entities_to_read.items()
            if info['scan_interval'] == timedelta(seconds=0) and now >= info['next_read_time']
        ]
        return sorted(entities_without_interval, key=lambda item: item[1]['next_read_time'])

    async def read_entities_periodically(self):
        while True:
            await asyncio.sleep(1)
            now = datetime.now()

            sorted_entities_with_interval = self._get_sorted_entities_with_interval(now)

            for entity_id, info in sorted_entities_with_interval:
                await self.process_entity_reading(entity_id, info, info['scan_interval'])
                break
            else:
                sorted_entities_without_interval = self._get_sorted_entities_without_interval(now)
                for entity_id, info in sorted_entities_without_interval:
                    await self.process_entity_reading(entity_id, info, self.default_read_interval)
                    break

    async def process_entity_reading(self, entity_id, info, interval):
        _LOGGER.debug(f"Entity {entity_id} is due for reading")
        try:
            _LOGGER.info(f"Reading data from entity {entity_id}")
            if self.hass.states.get(entity_id):
                await self.hass.services.async_call(
                    'homeassistant', 'update_entity', {'entity_id': entity_id}
                )
                if entity_id in self.entities_to_read:
                    now = datetime.now()
                    self.entities_to_read[entity_id]['last_read'] = now
                    self.entities_to_read[entity_id]['next_read_time'] = now + interval
            else:
                _LOGGER.warning(f"Entity {entity_id} not found, removing from list")
                del self.entities_to_read[entity_id]
        except Exception as e:
            _LOGGER.error(f"Error reading entity {entity_id}: {e}")
