#Scheduler for periodic reading of Buspro entities

import asyncio
import logging
from datetime import datetime, timedelta
from homeassistant.helpers.entity_registry import async_get

_LOGGER = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, hass):
        _LOGGER.debug("Initializing Scheduler")
        self.hass = hass
        self.entities_to_read = {}
        self.default_read_interval = timedelta(seconds=10)
        self.busy = False

    async def read_entities_periodically(self):
        _LOGGER.debug("Starting periodic entity reading")
        entity_registry = async_get(self.hass)
        _LOGGER.debug(f"Entity Registry")

        for entity_id, entity in entity_registry.entities.items():
            if entity.platform == 'buspro':
                scan_interval = entity.options.get('scan_interval', self.default_read_interval.total_seconds())
                self.entities_to_read[entity_id] = {
                    'last_read': datetime.min,
                    'scan_interval': timedelta(seconds=scan_interval)
                }

        while True:
            now = datetime.now()
            sorted_entities = sorted(
                self.entities_to_read.items(),
                key=lambda item: (now - item[1]['last_read'] >= item[1]['scan_interval'], item[1]['last_read'])
            )
            for entity_id, info in sorted_entities:
                if now - info['last_read'] >= info['scan_interval']:
                    _LOGGER.debug(f"Entity {entity_id} is due for reading")
                    try:
                        await self.read_entity(entity_id)
                        if entity_id in self.entities_to_read:
                            self.entities_to_read[entity_id]['last_read'] = now
                    except Exception as e:
                        _LOGGER.error(f"Error reading entity {entity_id}: {e}")
                    break

            await asyncio.sleep(1)

    async def read_entity(self, entity_id):
        _LOGGER.info(f"Reading data from entity {entity_id}")
        if self.hass.states.get(entity_id):
            await self.hass.services.async_call(
                'homeassistant', 'update_entity', {'entity_id': entity_id}
            )
        else:
            _LOGGER.warning(f"Entity {entity_id} not found, removing from list")
            del self.entities_to_read[entity_id]
