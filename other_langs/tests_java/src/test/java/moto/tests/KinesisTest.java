package moto.tests;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.core.SdkSystemSetting;
import software.amazon.awssdk.services.kinesis.KinesisClient;
import software.amazon.awssdk.services.kinesis.model.*;

import java.math.BigInteger;
import java.util.Comparator;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class KinesisTest {

    private static final BigInteger MAX_HASH_KEY = new BigInteger("2").pow(128).subtract(BigInteger.ONE);

    static {
        System.setProperty(SdkSystemSetting.CBOR_ENABLED.property(), "false");
    }

    @Test
    void lastShardEndingHashKeyIsMaxValue() {
        KinesisClient client = DependencyFactory.kinesisClient();
        String streamName = "test-stream-" + System.currentTimeMillis();
        int shardCount = 4;

        client.createStream(CreateStreamRequest.builder()
                .streamName(streamName)
                .shardCount(shardCount)
                .build());

        ListShardsResponse response = client.listShards(ListShardsRequest.builder()
                .streamName(streamName)
                .build());

        List<Shard> shards = response.shards();
        assertEquals(shardCount, shards.size());

        Shard lastShard = shards.stream()
                .max(Comparator.comparing(s -> new BigInteger(s.hashKeyRange().endingHashKey())))
                .orElseThrow();

        assertEquals(MAX_HASH_KEY, new BigInteger(lastShard.hashKeyRange().endingHashKey()));
    }

    @Test
    void shardHashRangesCoverFullKeySpace() {
        KinesisClient client = DependencyFactory.kinesisClient();
        String streamName = "test-stream-coverage-" + System.currentTimeMillis();
        int shardCount = 4;

        client.createStream(CreateStreamRequest.builder()
                .streamName(streamName)
                .shardCount(shardCount)
                .build());

        ListShardsResponse response = client.listShards(ListShardsRequest.builder()
                .streamName(streamName)
                .build());

        List<Shard> shards = response.shards().stream()
                .sorted(Comparator.comparing(s -> new BigInteger(s.hashKeyRange().startingHashKey())))
                .toList();

        assertEquals(BigInteger.ZERO, new BigInteger(shards.get(0).hashKeyRange().startingHashKey()));
        assertEquals(MAX_HASH_KEY, new BigInteger(shards.get(shards.size() - 1).hashKeyRange().endingHashKey()));

        // Verify no gaps between shards
        for (int i = 1; i < shards.size(); i++) {
            BigInteger prevEnd = new BigInteger(shards.get(i - 1).hashKeyRange().endingHashKey());
            BigInteger currStart = new BigInteger(shards.get(i).hashKeyRange().startingHashKey());
            assertEquals(prevEnd.add(BigInteger.ONE), currStart,
                    "Gap between shard " + (i - 1) + " and shard " + i);
        }
    }
}
