from abc import ABC, abstractmethod

class CompilerInterface(ABC):
    """
    Abstract base class for compiling Expert Advisors.
    This allows us to seamlessly swap out the dummy compiler used on Render (Linux)
    with the actual MetaEditor compiler when running locally on Windows.
    """

    @abstractmethod
    async def compile(self, job, license_obj, order, user, storage_dir, telegram_token) -> bool:
        """
        Executes the compilation process.

        Args:
            job: The CompileJob object from the database.
            license_obj: The License object representing the customer's license.
            order: The Order object.
            user: The User object (contains the telegram_id).
            storage_dir: The directory workspace assigned for this compilation.
            telegram_token: The bot token used to send messages to the user.

        Returns:
            bool: True if compilation was successful and delivered, False otherwise.
        """
        pass
