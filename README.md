# Custom Network Protocol

A Python project implementing a custom, reliable protocol for client-server communication. This protocol features connection negotiation, error detection, selectable reliability strategies (Go-Back-N and Selective Repeat), and is designed for extensibility and experimentation.

---

## 🚀 Features

- **Custom Packet Structure:** Each packet includes payload length, message type, sequence number, and checksum for integrity.
- **Three-Way Handshake:** Secure connection establishment with parameter negotiation.
- **Operation Modes:** Step-by-step (stop-and-wait) and burst (windowed) communication.
- **Protocol Selection:** Go-Back-N or Selective Repeat for reliability.
- **Dynamic Packet Sizing:** Client negotiates the maximum packet size; messages are fragmented if needed.
- **Error Handling:** MD5 checksums, sequence numbers, and error simulation for robust testing.
- **Channel Reset:** Client can reset the channel and connection parameters interactively.
- **Extensible:** Easy to add new message types or protocol features.

---

## 🏁 Quick Start

1. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Server**
   ```bash
   python3 -m src.server
   ```
   (Listens on port 5000 by default)
3. **Run the Client**
   ```bash
   python3 -m src.client --host <SERVER_IP>
   ```
   Replace `<SERVER_IP>` with the server’s IP address.

---

## 📦 Protocol Overview

### Packet Format

| Field           | Size      | Description                        |
|-----------------|-----------|------------------------------------|
| Payload Length  | 4 bytes   | Size of payload                    |
| Message Type    | 1 byte    | SYN, ACK, DATA, etc.               |
| Sequence Number | 2 bytes   | For ordering and reliability       |
| Checksum        | 4 bytes   | MD5 hash of payload                |
| Payload         | variable  | Actual data                        |

### Message Types

- `SYN (0x01)`: Initiate connection
- `ACK (0x02)`: Acknowledge receipt
- `ACK_FINAL (0x03)`: Final handshake ack
- `DATA (0x04)`: Data transfer
- `DISCONNECT (0x05)`: End connection
- `SPECIAL (0x99)`: Channel error indicator

### Connection Flow

1. **Client → Server:** SYN (with parameters)
2. **Server → Client:** SYN-ACK (negotiated params)
3. **Client → Server:** ACK_FINAL
4. **Data Exchange:** DATA/ACK as per protocol
5. **Disconnect:** DISCONNECT/ACK

### Error Handling

- **Checksum:** Detects payload corruption.
- **Sequence Numbers:** Ensures correct ordering.
- **Timeouts:** Handles lost packets.
- **Channel Simulation:** Test with induced errors.

---

## 🗂️ Project Structure

- `src/network_device.py`: Base class for packet creation/parsing.
- `src/server.py`: Server logic, connection handling, handshake, and message processing.
- `src/client.py`: Client logic, connection, message sending, and interactive session.
- `src/core/settings.py`: Protocol constants and configuration.
- `src/constants/`: Additional constants for client/server.

---

## 🛠️ Extending the Protocol

- Add new message types in `settings.py` and implement handling in client/server.
- Implement new reliability or security features as needed.

---

## 📝 Notes

- The client can reset the channel and parameters at any time (option 5 in the menu).
- If an error is detected, the server closes the connection; the client must reconnect.
- The protocol is designed for easy extension and experimentation with networking concepts.

---

## 📖 Learn More

- See code comments and logs for detailed flow and debugging.
- Explore `src/network_device.py` for packet structure and parsing logic.
- Experiment with different operation modes and packet sizes.

---

## Example Usage

Start the server (default: all interfaces, port 5000):
```bash
python3 -m src.server
```

Start the client (specify server IP):
```bash
python3 -m src.client --host <SERVER_IP>
```

---

## Contribution

Feel free to open issues or submit pull requests to improve the protocol, add features, or suggest enhancements.

---

## License

This project is open source and available under the MIT License.