import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class DatabaseHelper {
    
    private static final String DB_URL = "jdbc:mysql://localhost:3306/testdb";
    private static final String USER = "user";
    private static final String PASS = "password";
    
    public String getUsers() {
        try (Connection conn = DriverManager.getConnection(DB_URL, USER, PASS);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT * FROM users")) {
            
            StringBuilder result = new StringBuilder();
            while (rs.next()) {
                result.append(rs.getString("name")).append(",");
            }
            
            return result.toString();
        } catch (SQLException e) {
            return "Error: " + e.getMessage();
        }
    }
    
    public int getUserCount() {
        try (Connection conn = DriverManager.getConnection(DB_URL, USER, PASS);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM users")) {
            
            if (rs.next()) {
                return rs.getInt(1);
            }
            
        } catch (SQLException e) {
            // Handle exception
        }
        
        return 0;
    }
}