# coding=utf-8
import logging

import influxdb
from influxdb.exceptions import InfluxDBClientError

log = logging.getLogger(__name__)


class CustomInfluxDBClient(influxdb.InfluxDBClient):
    def count(self, measurement, count=1, **kwargs):
        try:
            self.write_points([{
                "measurement": measurement,
                "tags": kwargs,
                "fields": {
                    "value": count
                }
            }])
        except InfluxDBClientError as e:
            log.error("Encountered error pushing stats point.")
            log.error(e)
