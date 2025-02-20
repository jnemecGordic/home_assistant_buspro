# Scheduler for periodic reading of Buspro entities

import asyncio
import logging
from datetime import datetime, timedelta
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, hass):
        self.hass = hass
        self.entities_to_read = {}
        self.default_read_interval = 10  # seconds
        self._now = self.hass.loop.time()

    async def add_entity(self, entity):
        entity_id = entity.entity_id
        scan_interval = entity.scan_interval
        
        if scan_interval is None or scan_interval == 0:
            seconds = 0
        else:
            try:
                seconds = int(scan_interval)
            except ValueError:
                _LOGGER.error(f"Invalid scan_interval for entity {entity_id}: {scan_interval}")
                seconds = self.default_read_interval

        self.entities_to_read[entity_id] = {
            'scan_interval': seconds,
            'next_read_time': self.hass.loop.time() + seconds
        }
        _LOGGER.debug(f"Adding entity {entity_id} to scheduler scan_interval {seconds}s")

    def _get_sorted_entities_with_interval(self):
        entities_with_interval = [
            (entity_id, info) for entity_id, info in self.entities_to_read.items()
            if info['scan_interval'] > 0 and self._now >= info['next_read_time']
        ]
        return sorted(entities_with_interval, key=lambda item: item[1]['next_read_time'])

    def _get_sorted_entities_without_interval(self):
        entities_without_interval = [
            (entity_id, info) for entity_id, info in self.entities_to_read.items()
            if info['scan_interval'] == 0 and self._now >= info['next_read_time']
        ]
        return sorted(entities_without_interval, key=lambda item: item[1]['next_read_time'])

    async def read_entities_periodically(self):
        # wait to start until HA is running
        if not self.hass.is_running:
            startup_event = asyncio.Event()
            
            @callback
            def ha_started(_):
                _LOGGER.info("Home Assistant started - beginning periodic entity reading")
                startup_event.set()
                
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, ha_started)
            await startup_event.wait()
            
        # main loop
        while not self.hass.is_stopping:            
            self._now = self.hass.loop.time()
            sorted_entities_with_interval = self._get_sorted_entities_with_interval()

            for entity_id, info in sorted_entities_with_interval:
                await self.process_entity_reading(entity_id, info, info['scan_interval'])
                break
            else:
                sorted_entities_without_interval = self._get_sorted_entities_without_interval()
                for entity_id, info in sorted_entities_without_interval:
                    await self.process_entity_reading(entity_id, info, self.default_read_interval)
                    break
            await asyncio.sleep(1)

    async def process_entity_reading(self, entity_id, info, interval):
        _LOGGER.debug(f"Entity {entity_id} is due for reading")
        try:
            _LOGGER.info(f"Reading data from entity {entity_id}")
            if self.hass.states.get(entity_id):
                await self.hass.services.async_call(
                    'homeassistant', 'update_entity', {'entity_id': entity_id}
                )
                if entity_id in self.entities_to_read:
                    self.entities_to_read[entity_id]['next_read_time'] = self._now + interval
            else:
                _LOGGER.warning(f"Entity {entity_id} not found, removing from list")
                del self.entities_to_read[entity_id]
        except Exception as e:
            _LOGGER.error(f"Error reading entity {entity_id}: {e}")

    async def device_updated(self, entity_id: str):
        if entity_id not in self.entities_to_read:
            return
        
        current_time = self.hass.loop.time()
        if current_time - self._now > 1:
            self._now = current_time

        info = self.entities_to_read[entity_id]
        interval = info['scan_interval'] if info['scan_interval'] > 0 else self.default_read_interval
        info['next_read_time'] = self._now + interval
       