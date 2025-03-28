CC = gcc
CFLAGS = -Wall -Wextra -g
LDFLAGS = -pthread
OBJ_DIR = obj
BIN_DIR = bin

# Source files
SERVER_SRC = server.c
CLIENT_SRC = client.c

# Object files
SERVER_OBJ = $(patsubst %.c,$(OBJ_DIR)/%.o,$(SERVER_SRC))
CLIENT_OBJ = $(patsubst %.c,$(OBJ_DIR)/%.o,$(CLIENT_SRC))

# Binary targets
SERVER = $(BIN_DIR)/server
CLIENT = $(BIN_DIR)/client

# Default target
all: dirs $(SERVER) $(CLIENT)

# Create necessary directories
dirs:
	mkdir -p $(OBJ_DIR) $(BIN_DIR)

# Compile server
$(SERVER): $(SERVER_OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Compile client
$(CLIENT): $(CLIENT_OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Compile C source files
$(OBJ_DIR)/%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@


# Clean build files
clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)

# Run the server
run-server: $(SERVER)
	./$(SERVER)

# Run the client
run-client: $(CLIENT)
	./$(CLIENT)

# Test with simulated errors (0-100% chance of error)
test-error: all
	./$(SERVER) --error-rate=20 &
	sleep 1
	./$(CLIENT) --error-simulation

# Test with batch mode
test-batch: all
	./$(SERVER) --batch-mode &
	sleep 1
	./$(CLIENT) --batch-mode

# Phony targets
.PHONY: all clean dirs run-server run-client test-error test-batch
