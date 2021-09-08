
import ndjson
import datetime as dt

class Transaction():
    def __init__(self, merchant: str = "", amount: int = 0, time: dt = None) -> None:
        self.merchant = merchant
        self.amount = amount
        self.time = time
        self.approved = True
    
    def set_approval(self, approved: bool = True) -> None:
        self.approved = approved


class Account():
    def __init__(self, active_card: bool = True, available_limit: int = 0) -> None:
        self.active_card = active_card
        self.available_limit = available_limit

    def transact(self, transaction: Transaction) -> None:
        self.available_limit = self.available_limit - transaction.amount


class Authorizer():
    def __init__(self) -> None:
        self.account: Account = None
        self.history: list[dict] = []
        self.transactions: list[Transaction] = []

    def save_operation(self, violations: list[str] = []):
        self.history.append(
            {
                "account": {
                    "active-card": self.account.active_card,
                    "available-limit": self.account.available_limit
                },
                "violations": violations
            }
        )

    def create_account(self, active_card: bool = True, available_limit: int = 0) -> None:
        if self.account is None:
            self.account = Account(active_card, available_limit)
            self.save_operation([])
        else:
            self.save_operation(["account-already-initialized"])

    def analyze_transaction(self, transaction: Transaction) -> list[str]:
        violations = []
        violation_checkers = [
            self.account_not_initialized,
            self.card_not_active,
            self.insufficient_limit,
            self.high_frequency_small_interval,
            self.doubled_transaction
        ]

        for checker in violation_checkers:
            if checker(transaction):
                violations.append(self.__get_violation__(checker))

        return violations

    def authorize(self, transaction: Transaction) -> None:
        violations = self.analyze_transaction(transaction)
        if len(violations) == 0:
            self.account.transact(transaction)
            transaction.set_approval(True)
        else:
            transaction.set_approval(False)
        self.save_operation(violations)
        self.transactions.append(transaction)
        
    def account_not_initialized(self, transaction) -> bool:
        return self.account is None

    def card_not_active(self, transaction) -> bool:
        return self.account is not None and not self.account.active_card

    def insufficient_limit(self, transaction) -> bool:
        return self.account is not None and self.account.available_limit < transaction.amount
    
    def high_frequency_small_interval(self, transaction) -> bool:
        last_transactions = self.__most_recent_transactions__(time=transaction.time)
        return len(last_transactions) > 2 and all(
            t.approved 
            for t in last_transactions
        )

    def doubled_transaction(self, transaction) -> bool:
        last_transactions = self.__most_recent_transactions__(time=transaction.time, quantity=2)
        return len(last_transactions) > 0 and any(
            t.approved 
            and self.__same_transaction__(t, transaction) 
            for t in last_transactions
        )

    def __most_recent_transactions__(self, time: dt, quantity: int = 3) -> list[Transaction]:
        most_recent_transactions = []
        delta = dt.timedelta(minutes=2)
        for t in self.transactions[::-1]:
            if (time - t.time) <= delta:
                most_recent_transactions.append(t)
            if len(most_recent_transactions) == quantity:
                break
        return most_recent_transactions

    def __same_transaction__(self, t1, t2) -> bool:
        return t1.merchant == t2.merchant and t1.amount == t2.amount

    def __get_violation__(self, checker) -> str:
        return checker.__name__.replace("_", "-")


if __name__ == "__main__":
    authorizer = Authorizer()

    with open("input.json") as f:
        input = ndjson.loads(f.read())

    for json_input in input:
        if "account" in list(json_input.keys()):
            active_card = json_input.get("account").get("active-card")
            available_limit = json_input.get("account").get("available-limit")
            authorizer.create_account(active_card, available_limit)
        else:
            merchant = json_input.get("transaction").get("merchant")
            amount = json_input.get("transaction").get("amount")
            time = json_input.get("transaction").get("time")
            time = dt.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")
            
            transaction = Transaction(merchant ,amount, time)
            authorizer.authorize(transaction)
    
    with open("output.json", "w") as f:
        for op in authorizer.history:
            f.write("%s\n" % op)
