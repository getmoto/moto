package moto.tests;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import software.amazon.awssdk.services.dynamodb.model.ResourceInUseException;

public class DynamoTest {

    @Test
    public void testSingleTableExists() {
        String tableName = "table" + System.currentTimeMillis();

        DynamoLogic logic = new DynamoLogic();
        String tableNameFromCreation = logic.createTable(tableName, "key");

        assertEquals(tableName, tableNameFromCreation);
    }

    @Test
    public void testTableCannotBeCreatedTwice() {
        String tableName = "table" + System.currentTimeMillis();
        DynamoLogic logic = new DynamoLogic();
        // Going once...
        logic.createTable(tableName, "key");
        try {
            // Going twice should throw a specific exception
            logic.createTable(tableName, "key");
        } catch (ResourceInUseException riue) {
            assertTrue(riue.getMessage().startsWith("Table already exists: " + tableName));
        }
    }
}
