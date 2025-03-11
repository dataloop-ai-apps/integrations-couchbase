import os
import logging
from datetime import timedelta
import dtlpy as dl

from couchbase.exceptions import CouchbaseException
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions, TransactionQueryOptions

logger = logging.getLogger(name="couchbase-connect")


class CouchbaseBase(dl.BaseServiceRunner):
    """
    A class for running a service that interacts with Couchbase.
    """

    def __init__(self):
        """
        Initializes the ServiceRunner with Couchbase credentials.
        """
        self.logger = logger


    def couchbase_to_dataloop(
        self,
        endpoint: str,
        username: str,
        bucket: str,
        scope: str,
        collection: str,
        dataset_id: str,
    ):
        """
        Creates a PromptItem for each document in the specified Couchbase collection and uploads them to the specified Dataloop dataset.

        :param endpoint: The hostname of the Couchbase cluster.
        :param username: The username for the Couchbase cluster.
        :param bucket: The name of the  bucket.
        :param scope: The name of the scope.
        :param collection: The name of the collection.
        :param dataset_id: The ID of the Dataloop dataset.
        :return: A list of the uploaded PromptItems or None if an error occurs.
        """

        self.logger.info(
            "Creating table for dataset '%s' and collection '%s'.",
            dataset_id,
            collection,
        )

        try:
            dataset = dl.datasets.get(dataset_id=dataset_id)
            self.logger.info("Successfully retrieved dataset with ID '%s'.", dataset_id)
        except dl.exceptions.NotFound as e:
            self.logger.error("Failed to get dataset with ID '%s': %s", dataset_id, e)
            return None
        
        password = os.environ.get("COUCHBASE_PASSWORD")
        auth = PasswordAuthenticator(username, password)

        try:
            cluster = Cluster(endpoint, ClusterOptions(auth))
            cluster.wait_until_ready(timedelta(seconds=5))
            bucket = cluster.bucket(bucket)
            scope = bucket.scope(scope)
            query = f"SELECT META({collection}).id AS _id, * FROM {collection}"
            result = scope.query(query)


        except CouchbaseException as e:
            self.logger.error("Failed to connect to Couchbase: %s", e)
            raise e

        prompt_items = []
        for row in result:
            prompt_item = dl.PromptItem(name=row["_id"])
            prompt_item.add(
                message={
                    "role": "user",
                    "content": [
                        {
                            "mimetype": dl.PromptType.TEXT,
                            "value": row[collection]["prompt"],
                        }
                    ],
                }
            )
            prompt_items.append(prompt_item)

        items = dataset.items.upload(local_path=prompt_items, overwrite=True,return_as_list=True,raise_on_error=True)

        self.logger.info(
            "Successfully uploaded %d items to dataset '%s'.", len(items), dataset_id
        )
        return items

    def update_document(
        self, item: dl.Item, endpoint: str, username: str, bucket: str, scope: str, collection: str
    ):
        """
        Updates the specified Couchbase collection document with the best response for the specified item.

        :param item: The item to update.
        :param endpoint: The endpoint for the Couchbase cluster.
        :param username: The username for the Couchbase cluster.
        :param bucket: The name of the bucket.
        :param scope: The name of the scope.
        :param collection: The name of the collection.
        :return: The updated item or None if an error occurs.
        """

        self.logger.info(
            "Updating collection '%s' for item with ID '%s'.", collection, item.id
        )

        prompt_item = dl.PromptItem.from_item(item)
        first_prompt_key = prompt_item.prompts[0].key

        # Find the best response based on annotation attributes
        best_response = None
        model_id, name = None, "human"  # Default value for 'name' if not found

        for resp in item.annotations.list():
            try:
                is_best = resp.attributes.get("isBest", False)
            except AttributeError:
                is_best = False
            if is_best and resp.metadata["system"].get("promptId") == first_prompt_key:
                best_response = resp.coordinates
                model_info = resp.metadata.get("user", {}).get("model", {})
                model_id = model_info.get("model_id", "")
                name = model_info.get("name", "human")
                break

        if best_response is None:
            self.logger.error("No best response found for item ID: '%s'", item.id)
            raise ValueError(f"No best response found for item ID: '{item.id}'")
        
        doc_id = prompt_item.name[:-5] #remove the .json extension

        try:
            password = os.environ.get("COUCHBASE_PASSWORD")
            auth = PasswordAuthenticator(username, password)
            cluster = Cluster(endpoint, ClusterOptions(auth))
            cluster.wait_until_ready(timedelta(seconds=5))
            def txn_logic(ctx, bucket_name, scope_name, collection_name, doc_id, response_text):
                query = f"""
                UPDATE `{bucket_name}`.`{scope_name}`.`{collection_name}`
                SET response = $response_text, model_id = "{model_id}", name = "{name}"
                WHERE META().id = $doc_id
                """
                ctx.query(query, TransactionQueryOptions(named_parameters={"response_text": response_text, "doc_id": doc_id}))

            cluster.transactions.run(lambda ctx: txn_logic(ctx, bucket, scope, collection, doc_id, best_response))
            print("Transaction committed successfully!")

        except Exception as e:
            self.logger.error("Transaction failed: %s", e)
            raise e

        self.logger.info(
            "Successfully updated document from collection '%s' for item with ID '%s'.",
            collection,
            item.id,
        )
        return item
