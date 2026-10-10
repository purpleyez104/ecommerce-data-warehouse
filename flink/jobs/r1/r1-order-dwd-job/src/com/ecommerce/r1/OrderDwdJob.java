package com.ecommerce.r1;

import java.io.IOException;
import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.util.Properties;

import org.apache.doris.flink.cfg.DorisExecutionOptions;
import org.apache.doris.flink.cfg.DorisOptions;
import org.apache.doris.flink.cfg.DorisReadOptions;
import org.apache.doris.flink.sink.DorisSink;
import org.apache.doris.flink.sink.writer.serializer.SimpleStringSerializer;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.RichFlatMapFunction;
import org.apache.flink.util.Collector;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.JsonNode;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.kafka.clients.consumer.ConsumerRecord;

/** R1 development job: single-active-partition Kafka CDC -> Doris current-order DWD. */
public final class OrderDwdJob {
    private static final String TOPIC = "ods_cdc_m2_clean_v1";
    private static final String DATABASE = "ecommerce_oltp_m2_acceptance";
    private static final String BROKERS = "hadoop201:9092,hadoop202:9092,hadoop203:9092";
    private static final String CHECKPOINT =
            "hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/order_dwd_r1_v1";

    /** Kafka metadata must travel with each source record; raw Debezium JSON omits offsets. */
    public static final class CdcRecord implements Serializable {
        public String json;
        public int partition;
        public long offset;

        public CdcRecord() {}
        public CdcRecord(String json, int partition, long offset) {
            this.json = json;
            this.partition = partition;
            this.offset = offset;
        }
    }

    public static final class WithMetadata implements KafkaRecordDeserializationSchema<CdcRecord> {
        @Override
        public void deserialize(ConsumerRecord<byte[], byte[]> record, Collector<CdcRecord> output)
                throws IOException {
            if (record.value() == null) {
                throw new IOException("Unexpected null Kafka CDC value at offset=" + record.offset());
            }
            output.collect(new CdcRecord(
                    new String(record.value(), StandardCharsets.UTF_8),
                    record.partition(), record.offset()));
        }

        @Override
        public TypeInformation<CdcRecord> getProducedType() {
            return TypeInformation.of(CdcRecord.class);
        }
    }

    public static final class CleanOrder extends RichFlatMapFunction<CdcRecord, String> {
        private transient ObjectMapper mapper;

        @Override
        public void flatMap(CdcRecord record, Collector<String> out) throws Exception {
            if (mapper == null) mapper = new ObjectMapper();
            JsonNode event = mapper.readTree(record.json);
            if (event == null || !event.isObject()) {
                throw new IOException("Invalid CDC JSON at Kafka offset=" + record.offset);
            }
            // This topic uses a plain Debezium JSON envelope (no payload wrapper).
            if (event.has("payload") && event.get("payload").isObject()) {
                event = event.get("payload");
            }
            JsonNode source = event.path("source");
            if (!DATABASE.equals(source.path("db").asText()) ||
                    !"biz_order".equals(source.path("table").asText())) return;

            if (record.partition != 0) {
                throw new IOException("Order event found in partition=" + record.partition
                        + "; kafka_offset sequence is only valid for partition 0");
            }

            String op = event.path("op").asText();
            if ("d".equals(op)) {
                throw new IOException("Physical order DELETE requires explicit DWD delete handling; "
                        + "refuse silent data loss at offset=" + record.offset);
            }
            if (!("c".equals(op) || "u".equals(op) || "r".equals(op))) {
                throw new IOException("Unexpected order CDC operation=" + op);
            }

            JsonNode after = event.path("after");
            if (!after.isObject()) {
                throw new IOException("Order after is not an object at offset=" + record.offset);
            }
            String status = after.path("order_status").asText();
            if (!("CREATED".equals(status) || "PAID".equals(status) || "CANCELED".equals(status))) {
                throw new IOException("Unexpected order status at offset=" + record.offset);
            }
            if (!after.path("order_id").canConvertToLong() ||
                    !after.path("gross_amount_cents").canConvertToLong() ||
                    !after.path("discount_amount_cents").canConvertToLong() ||
                    !after.path("payable_amount_cents").canConvertToLong()) {
                throw new IOException("Missing or invalid required numeric fields at offset=" + record.offset);
            }
            long gross = after.path("gross_amount_cents").asLong();
            long discount = after.path("discount_amount_cents").asLong();
            long payable = after.path("payable_amount_cents").asLong();
            if (gross < 0 || discount < 0 || payable < 0 || discount > gross ||
                    gross - discount != payable) {
                throw new IOException("Order amount rule violation at offset=" + record.offset);
            }
            for (String name : new String[] {"order_no", "created_at",
                    "payment_deadline_at", "updated_at"}) {
                if (!after.path(name).isTextual()) {
                    throw new IOException("Missing mandatory order field " + name +
                            " at offset=" + record.offset);
                }
            }
            ObjectNode row = (ObjectNode) after.deepCopy();
            row.put("kafka_partition", record.partition);
            row.put("kafka_offset", record.offset);
            out.collect(mapper.writeValueAsString(row));
        }
    }

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1);
        env.enableCheckpointing(30_000L);
        env.getCheckpointConfig().setCheckpointStorage(CHECKPOINT);
        env.getCheckpointConfig().setCheckpointTimeout(120_000L);
        env.getCheckpointConfig().setMinPauseBetweenCheckpoints(10_000L);

        KafkaSource<CdcRecord> kafka = KafkaSource.<CdcRecord>builder()
                .setBootstrapServers(BROKERS)
                .setTopics(TOPIC)
                .setGroupId("r1_dwd_order_v1")
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setDeserializer(new WithMetadata())
                .build();

        DorisOptions doris = DorisOptions.builder()
                .setFenodes("hadoop201:18030")
                .setTableIdentifier("ecommerce_serving.dwd_order")
                .setUsername("root")
                .setPassword("")
                .build();
        Properties load = new Properties();
        load.setProperty("format", "json");
        load.setProperty("read_json_by_line", "true");
        DorisExecutionOptions execution = DorisExecutionOptions.builder()
                .setLabelPrefix("r1_dwd_order_v1")
                .setDeletable(false)
                .enable2PC()
                .setStreamLoadProp(load)
                .build();
        DorisSink<String> sink = DorisSink.<String>builder()
                .setDorisReadOptions(DorisReadOptions.builder().build())
                .setDorisExecutionOptions(execution)
                .setDorisOptions(doris)
                .setSerializer(new SimpleStringSerializer())
                .build();

        env.fromSource(kafka, WatermarkStrategy.noWatermarks(), "Kafka CDC raw")
                .flatMap(new CleanOrder())
                .name("DWD order validation and JSON normalization")
                .sinkTo(sink)
                .name("Doris dwd_order");
        env.execute("R1 order CDC to Doris DWD");
    }
}
