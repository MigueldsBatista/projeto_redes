#include <stdio.h>
#include <arpa/inet.h>   // For internet operations (sockaddr_in, htons, etc.)
#include <string.h>      // String functions (strlen)
#include <sys/socket.h>  // Socket definitions and functions
#include <unistd.h>      // For close() function
#include <stdlib.h>      // For memory allocation functions
#define PORT 8080        // Define server port number
#define BUFFER_SIZE 1024 // Define buffer size

int main()
{
    //------------------------------------------------------------------------------------------------------------------
    int status, response_read, client_file_descriptor, response_status;      // Variables for status, bytes read, and socket file descriptor
    struct sockaddr_in server_address;        // Server address structure
    char message[BUFFER_SIZE] = { 0 };        // Fixed: properly allocate memory for message
   
    char server_buffer[1024] = { 0 };           // buffer to store received data, initialized to zeros
    //------------------------------------------------------------------------------------------------------------------
    
    // Create a TCP socket

    //AF_INET is an acronym for Address Family Internet, which is used for IPv4 addresses.
    //SOCK_STREAM is used for TCP sockets, which provide a reliable, ordered, and error-checked delivery of a stream of data

    //------------------------------------------------------------------------------------------------------------------
    
    client_file_descriptor = socket(AF_INET, SOCK_STREAM, 0);

    if (client_file_descriptor < 0) { 
        printf("\n Socket creation error \n");
        return -1;
    }
    //------------------------------------------------------------------------------------------------------------------
    // Configure server address

    server_address.sin_family = AF_INET;          // IPv4
    server_address.sin_port = htons(PORT);        // Convert port to network byte order
    //htons is a function that converts a port number from host byte order to network byte order

    //------------------------------------------------------------------------------------------------------------------
    // Convert IP address from text format to binary format

    if (inet_pton(AF_INET, "127.0.0.1", &server_address.sin_addr) <= 0) {
        printf("\nInvalid address/ Address not supported \n");
        return -1;
    }
    //------------------------------------------------------------------------------------------------------------------
    // Connect to the server

    if ((status = connect(client_file_descriptor, (struct sockaddr*)&server_address, sizeof(server_address))) < 0) {
        printf("\nConnection Failed \n");
        return -1;
    }
    //------------------------------------------------------------------------------------------------------------------
    // Send message to server
    while (1) {
        memset(server_buffer, 0, BUFFER_SIZE); // Limpa o buffer antes de cada leitura
        memset(message, 0, BUFFER_SIZE);       // Clear message buffer

        printf("Type a message to the server: \n");
        scanf("%s", message);   // Message to send to server

        response_status = send(client_file_descriptor, message, strlen(message), 0);  // Fixed: added send function name
        
        if (response_status == -1) {
            printf("\nError sending message \n");
            return -1;
        }

        printf("Message sent\n");

        response_read = read(client_file_descriptor, server_buffer, 1024 - 1); // Leave space for null terminator
        printf("Response from server: \n");
        if (response_read == -1) {
            printf("\nError reading response \n");
            return -1;
        }
        printf("%s\n", server_buffer);
    }

    // Close the socket
    close(client_file_descriptor);
    return 0;
}
