# Couchbase Integration

This repository provides a service that enables seamless interaction between **Couchbase** and **Dataloop** using **user-password authentification**. The integration is designed to streamline data processing, collection updates, and data uploads between Couchbase and Dataloop datasets.

## Features

- **Secure Authentication** with **user-password authentication** for Couchbase access, ensuring secure and restricted access to sensitive data.
- **Dynamic Document Structure Creation and Updates**: Automatically create and update Couchbase collections based on Dataloop dataset information, allowing flexible schema-less data storage.
- **Flexible Query Execution**: Execute complex Couchbase queries directly from Dataloop using the integrated service, enabling seamless data retrieval and manipulation.
- **Seamless Data Upload**: Upload Couchbase query results directly to Dataloop datasets, streamlining data integration and accessibility across platforms.

## Prerequisites

To set up the integration, you'll need the following information:

- **Endpoint**: The endpoint for the Couchbase cluster.
- **Username**: The username for the Couchbase cluster with required permissions.
- **Password**: The password for the specified username.
- **Bucket, Scope and Collection**: In Couchbase, specify the bucket, scope and collection with at least the following key:
  - **`prompt`**: Represents the prompt to be created in Dataloop.

## Pipeline Nodes

- **Import Couchbase Collection**

  - This node retrieves documents from a specified Couchbase collection and adds them to a designated dataset in Dataloop, creating prompt items accordingly.

- **Export Couchbase document**
  - This node takes the response marked as the best and updates the corresponding document in the Couchbase collection with the response, model name, and ID from Dataloop.

## Acknowledgments

This project makes use of the following open-source software:

- **[Couchbaese](https://github.com/couchbase/couchbase-python-client)**: The Couchbase Python client, distributed under the [Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0). PyMongo provides tools for interacting with Couchbase in Python. For more information about Couchbase, visit its [documentation](https://docs.couchbase.com/home/index.html) or [GitHub repository](https://github.com/couchbase/couchbase-python-client).
