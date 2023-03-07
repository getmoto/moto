package moto.tests;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import software.amazon.awssdk.services.dynamodb.model.ResourceInUseException;

public class DynamoTest {

    @Test
    public void testSingleTableExists() {
        DynamoLogic logic = new DynamoLogic();
        String table_name = logic.createTable("table", "key");

        assertEquals("table", table_name);
    }

    @Test
    public void testTableCannotBeCreatedTwice() {
        DynamoLogic logic = new DynamoLogic();
        // Going once...
        logic.createTable("table2", "key");
        try {
            // Going twice should throw a specific exception
            logic.createTable("table2", "key");
        } catch (ResourceInUseException riue) {
            assertTrue(riue.getMessage().startsWith("Table already exists: table2"));
        }
    }
}
