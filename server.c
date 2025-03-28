#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <signal.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <asm-generic/socket.h>

#define PORT 8080
#define BUFFER_SIZE 1056

int server_fd, client_socket;

void handle_sigint() {
    printf("\nShutting down server...\n");
    close(client_socket);
    close(server_fd);
    exit(0);
}

int main()
{
    struct sockaddr_in address;
    int opt = 1;
    socklen_t addrlen = sizeof(address);
    char buffer[1024] = { 0 };

    // Setup signal handler
    signal(SIGINT, handle_sigint);

    // Creating socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Forcefully attaching socket to the port 8080
    if (setsockopt(
        server_fd,// socket file descriptor
        SOL_SOCKET,// level
        SO_REUSEADDR | SO_REUSEPORT,// option name
        &opt,// option 1 means reuse 
        sizeof(opt))
        )
    {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    // Forcefully attaching socket to the port 8080
    if (bind(server_fd, (struct sockaddr*)&address,
             sizeof(address))
        < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }
    if (listen(server_fd, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    printf("Server started on port %d\n", PORT);
    printf("Waiting for connections...\n");

    // Accept connection
    if ((client_socket = accept(server_fd, (struct sockaddr*)&address, &addrlen)) < 0) {
        perror("Accept failed");
        exit(EXIT_FAILURE);
    }

    printf("Client connected. Ready to receive messages.\n");

    // Communication loop
    while (1) {
        memset(buffer, 0, BUFFER_SIZE);

        // Receive message from client
        ssize_t bytes_received = recv(client_socket, buffer, BUFFER_SIZE - 1, 0);

        if (bytes_received < 0) {
            perror("Receive error");
            break;
        }

        if (bytes_received == 0) {
            printf("Client disconnected.\n");
            break;
        }

        printf("Client: %s\n", buffer);

        // Prepare and send response
        char response[BUFFER_SIZE];
        snprintf(
            response,
            BUFFER_SIZE,
            "Message '%s' received successfully",
            buffer
        );

        if (send(client_socket, response, strlen(response), 0) < 0) {
            perror("Send failed");
            break;
        }
    }

    // Cleanup
    close(client_socket);
    close(server_fd);

    return 0;
}

