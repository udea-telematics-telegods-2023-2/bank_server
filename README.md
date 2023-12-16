# TeleGods Bank Server

TeleGods Bank Server is part of the final project of the "Servicios Telemáticos" course
at Universidad de Antioquia. The assignment involves building three
applications: a bank server, a liquor store server, and a client for these two.
Each application is containerized and designed for easy deployment.

## Features

- Secure Communication: The server uses SSL to secure communication between
  endpoints.
- Keyword-based Communication: The bank server communicates using keywords,
  similar to FTP.
- Protocol Support: The server listens on both UDP and TCP sockets, acting as a
  pure server without initiating communication.
- Database Integration: User credentials and balances are stored in an SQLite
  database.

## Error Codes

### Server Error Codes

- **0:** No error
- **1:** Invalid login (User not found or incorrect password)
- **2:** Invalid registration (User already registered)
- **3:** Insufficient funds (Tried to withdraw or transfer more than it has)
- **4:** Insufficient stock (Not enough liquor)

### Client Error Codes

- **128:** Invalid IP
- **129:** Invalid port

### General Error Codes

- **251:** Unauthorized access
- **252:** UUID not found
- **253:** Bad arguments
- **254:** Unknown command
- **255:** Unknown error

## Getting Started

### Installation and Prerequisites

1. **Prerequisites:**

   - Ensure you have Docker or Podman installed on your machine.
   - Install OpenSSL if not already installed.

2. **Clone the Repository:**

   ```bash
   git clone https://github.com/udea-telematics-telegods-2023-2/bank_server.git
   cd bank_server
   ```

3. **Generate SSL Certificates:**
   - Edit and run the provided script to generate SSL certificates.
     ```bash
     chmod +x generate_certificates.sh
     ./generate_certificates.sh
     ```

### Deploying the Bank Server with Docker

1. **Build the Docker Image:**

   ```bash
   docker build -t telebank_server .
   ```

2. **Run the Docker Container:**

   - Replace `/path/to/cert` and `/path/to/key` with the actual paths where the
     SSL certificates are stored.

     ```bash
     docker run -v /path/to/cert:/app/credentials/telegods_bank.crt -v /path/to/key:/app/credentials/telegods_bank.key -p 8888:8888 telebank_server
     ```

   - This assumes your server is listening on port 8888. Adjust the `-p` flag if
     your server uses a different port.

3. **Access the Bank Server:**
   - Once the container is running, your TeleGods Bank Server should be
     accessible at `localhost:8888` (or the chosen port).

### Notes

- The SSL certificates (`telegods_bank.crt` and `telegods_bank.key`) should be
  generated and stored in a secure location on your host machine. Adjust the
  paths accordingly when running the Docker container.

- If you encounter any issues, please refer to the "Troubleshooting" section in
  the README or contact the project maintainers for assistance.

### Troubleshooting

If you encounter any issues during the installation or deployment process,
consider the following troubleshooting steps:

1. **Check Paths:**

   - Verify that the paths to SSL certificates are correct when running the
     Docker container.

2. **Port Conflicts:**

   - Ensure that the chosen port (8888 in this example) is not in use by other
     applications on your machine.

3. **Error Messages:**

   - Check the console output for any error messages or warnings during the
     Docker build and run processes.

4. **Contact Support:**
   - If issues persist, feel free to reach out to the project maintainers for
     assistance.

### Contributing

If you'd like to contribute to the development of the TeleGods Bank Server, send
me a mail ;).

### License

This project is licensed under the [GNU General Public License (GPL)](LICENSE) -
see the [LICENSE](LICENSE) file for details.

### Acknowledgments

- Assets taken from: https://www.flaticon.com/free-icons
