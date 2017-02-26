import influxdb

class CustomInfluxDBClient(influxdb.InfluxDBClient):
    def count(self, measurement, count=1, **kwargs):
        self.write_points([{
            "measurement": measurement,
            "tags": kwargs,
            "fields": {
                "value": count
            }
        }])
