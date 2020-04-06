from typing import List, Dict, Tuple
from enum import Enum, auto
from copy import copy
from abc import ABCMeta, abstractmethod
from type_check import type_check

class Singleton(object):
    def __new__(cls, *args, **keywords):
        if not hasattr(cls, "_instance"):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance

class Prototype(metaclass=ABCMeta):
    @abstractmethod
    def clone(self):
        pass

class Pd(Enum):
    NONE = auto()
    LAVOR = auto() # 労働
    MONEY = auto() # お金
    MEAL = auto() # ご飯

class World(Singleton):
    time = 0
    def next(self):
        World.time += 1

class Item:
    @type_check
    def __init__(self, name: Pd):
        self.name = name

class ItemFactory(Singleton):
    factory = dict()
    def get(self, name: Pd) -> Item:
        if name not in ItemFactory.factory.keys():
            ItemFactory.factory[name] = Item(name)
        return ItemFactory.factory[name]

class ItemSet: # amount >= 0を保証
    @type_check
    def __init__(self, name: Pd, amount: int):
        self.name = name
        self.item = ItemFactory().get(name) # FactoryからItem取得
        self.amount = amount

    def minus(self) -> 'ItemSet':
        return ItemSet(self.item.name, -self.amount)

class ItemCatalog(Prototype):
    @type_check
    def __init__(self, itemsets: List[ItemSet] = list()):
        self.dict: Dict[Item, int] = dict()
        if len(itemsets) > 0:
            self.put(itemsets)

    def clone(self):
        cloned_self = copy(self)
        cloned_self.dict = copy(self.dict)
        return cloned_self

    @type_check
    def add(self, itemset: ItemSet):
        if itemset.item in self.dict.keys():
            self.dict[itemset.item] += itemset.amount
        else:
            self.dict[itemset.item] = itemset.amount

    @type_check
    def add_no_minus(self, itemset: ItemSet):
        sum_amount = 0
        if itemset.item in self.dict.keys():
            sum_amount = self.dict[itemset.item]
        if sum_amount + itemset.amount < 0:
            # マイナス値があった場合はエラー
            raise MinusMergeError("MinusMergeError")
        else:
            self.add(itemset)

    @type_check
    def put(self, itemsets: List[ItemSet]):
        for itemset in itemsets:
            self.add(itemset)

    @type_check
    def get(self, item: Item) -> int:
        return self.dict[item]

    def merge(self, catalog: 'ItemCatalog') -> 'ItemCatalog':
        for item, amount in catalog.items():
            if item in self.keys():
                self.dict[item] += amount
            else:
                self.dict[item] = amount
        return self

    def merge_no_minus(self, catalog: 'ItemCatalog') -> 'ItemCatalog':
        # 自身のコピーにまずマージして検証
        merged_catalog = self.clone().merge(catalog)
        for item in catalog.keys():
            if merged_catalog.get(item) < 0:
                # マイナス値があった場合はエラー
                raise MinusMergeError("MinusMergeError")
        self.merge(catalog)
        return self

    def check_no_minus(self) -> 'ItemCatalog':
        for amount in self.values():
            if amount < 0:
                # マイナス値があった場合はエラー
                raise MinusMergeError("MinusMergeError")
        return self

    def minus(self) -> 'ItemCatalog':
        minus_self = ItemCatalog()
        for item, amount in self.items():
            minus_self.dict[item] = -amount
        return minus_self

    # Dictのメソッド
    def items(self):
        return self.dict.items()

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

class Expect:
    def __init__(self):
        self.forcast = 0 # 予測期間
        self.amount = 0 # 予測獲得量
        self._time = World().time # 最新獲得日
        self._count = 0 # 獲得回数

    @type_check
    def estimate(self, amount: int):
        # かかった期間
        term = World().time - self._time
        if term > 0:
            self._count += 1
            # 次の予想獲得単位時間（平滑移動平均）
            self.forcast = ((self._count-1)*self.forcast + term)/self._count
            # 単位時間あたりのItemの獲得量（平滑移動平均）
            self.amount = ((self._count-1)*self.amount + (amount/term))/self._count
            self._time = World().time
        # 同タイミングの場合
        else:
            self.amount = ((self._count-1)*self.amount + amount)/self._count

class Recipe:
    @type_check
    def __init__(self, srcset: ItemCatalog, dstset: ItemCatalog):
        self.srcset = srcset.check_no_minus().clone()
        self.dstset = dstset.check_no_minus().clone()

    @type_check
    def manufact(self, properties: ItemCatalog) -> bool:
        try:
            properties.merge_no_minus(self.srcset.minus())
        except MinusMergeError as e:
            print(e)
            return False
        properties.merge(self.dstset)
        return True

class Schedule:
    @type_check
    def __init__(self, duration: int):
        self.start = World.time
        self.duration = duration

class Agent:
    @type_check
    def __init__(self, name: str, products: ItemCatalog, nessesities: ItemCatalog, properties: ItemCatalog, schedule: Schedule):
        self.name = name
        self.products = products.check_no_minus().clone() # 単位時間に生産できるItemセット
        self.nessesities = nessesities.check_no_minus().clone() # World.time単位につき必要なItemセット
        self.properties = properties.check_no_minus().clone() # 所有Item初期設定
        self.schedule = schedule
        # Dict[Item,Expect]
        self.expects = {k: Expect() for k in nessesities.keys()}

    def produce(self):
        self.properties.merge(self.products)

    def consume(self):
        # 必要分を所有から差し引き
        self.properties.merge(self.nessesities.minus())

    @type_check
    def accept(self, diff: ItemSet):
        self.properties.add(diff)
        if diff.item in self.expects.keys():
            self.expects[diff.item].estimate(diff.amount)

    @type_check
    def pay(self, diff: ItemSet):
        self.accept(diff.minus())

    @type_check
    def manufact(self, recipe: Recipe):
        recipe.manufact(self.properties)

    @type_check
    def manufact_all(self, recipe: Recipe):
        while recipe.manufact(self.properties):
            pass

    def make_order(self) -> 'Order':
        if World.time - self.schedule.start >= self.schedule.duration:
            # 不足分を欲しい物セットに
            future_shortage = self.nessesities.minus().merge(self.properties)
            buysets = ItemCatalog([ItemSet(k.name, -v) for k, v in future_shortage.items() if v < 0])
            # 残り分を売り物セットに
            selsets = ItemCatalog([ItemSet(k.name, v) for k, v in future_shortage.items() if v > 0])
            return Order(self, buysets, selsets, self.schedule)

class Order:
    @type_check
    def __init__(self, agent: Agent, buy_goods: ItemCatalog, sel_goods: ItemCatalog, schedule: Schedule):
        self.agent = agent
        self.buy_goods = buy_goods.check_no_minus()
        self.sel_goods = sel_goods.check_no_minus()
        self.schedule = schedule

class Price:
    @type_check
    def __init__(self, goods: ItemSet, tag: ItemSet):
        if goods.amount != 1:
            raise NoUnitError("Goods's price should be defined by one!")
        self.goods = goods
        self.tag = tag

class Market:
    @type_check
    def __init__(self, marketprice: List[Price]):
        self.marketprice = marketprice
        self.clear_order()

    @type_check
    def add_order(self, order):
        if order is not None:
            self.request[order.agent] = order.buy_goods
            self.commodity[order.agent] = order.sel_goods

    def clear_order(self):
        self.request: Dict[Agent, ItemCatalog] = dict()
        self.commodity: Dict[Agent, ItemCatalog] = dict()

    def on_market(self):
        # 買い物客が
        for buyer, wants in self.request.items():
            # いろんな店舗に出向き
            for seller, goods in self.commodity.items():
                # もちろん自分の店舗以外で
                if buyer is not seller:
                    # 欲しい物がないか探す
                    for want, amount in wants.items():
                        # もし欲しい物があったら
                        if want in goods.keys():
                            # もしほしい数量在庫が存在していたら
                            if goods.get(want) >= amount:
                                # 買われる商品（欲しい量だけ）
                                bought = ItemSet(want.name, amount)
                                # 商品の値段
                                price = self.price_tag(bought)
                            # もしほしい数量より在庫が不足していたら
                            else:
                                # 買われる商品（在庫全部）
                                bought = ItemSet(want.name, goods.get(want))
                                # 商品の値段
                                price = self.price_tag(bought)
                            # 決済
                            buyer.accept(bought)
                            buyer.pay(price)
                            seller.accept(price)
                            seller.pay(bought)
                            print("{0}が{1}から{2}[{3}]を{4}[{5}]で購入".format(
                                    buyer.name, seller.name, 
                                    bought.name, bought.amount, 
                                    price.name, price.amount
                                ))

    def price_tag(self, itemset: ItemSet) -> ItemSet:
        for price in self.marketprice:
            if itemset.item is price.goods.item:
                return ItemSet(price.tag.name, price.tag.amount * itemset.amount)
        raise NoPriceError("No price is defined!")

class Error(Exception):
    def __init__(self, message):
        self.message = message

class MinusError(Error):
    pass

class MinusMergeError(Exception):
    pass

class NoUnitError(Error):
    pass

class NoPriceError(Error):
    pass

if __name__ == '__main__':
    # 商品と数の定義
    lavor1  = ItemSet(Pd.LAVOR, 1)
    money1  = ItemSet(Pd.MONEY, 1)
    meal1  = ItemSet(Pd.MEAL, 1)
    money100 = ItemSet(Pd.MONEY, 100)
    none0   = ItemSet(Pd.NONE, 0)

    # 商品と数のカタログの定義
    lavor1_c  = ItemCatalog([lavor1])
    money1_c  = ItemCatalog([money1])
    meal1_c  = ItemCatalog([meal1])
    money100_c = ItemCatalog([money100])
    none0_c   = ItemCatalog([none0])

    # 製造のレシピ
    rc1 = Recipe(lavor1_c, meal1_c)

    # オーダーの期限
    sch1 = Schedule(1)
    sch30 = Schedule(30)

    agents = list()
    names = ["A1", "A2", "A3"]
    for name in names:
        agents.append(Agent(name, lavor1_c, meal1_c, money1_c, sch1))

    plant = Agent("Plant", none0_c, lavor1_c, money100_c, sch1)

    mk = Market([Price(lavor1, money1), Price(meal1, money1)])

    while True:
        mk.clear_order
        for agent in agents:
            agent.produce() #生産
            agent.consume() #消費
            mk.add_order(agent.make_order()) #売買
        plant.manufact_all(rc1) #製造（変換）
        mk.add_order(plant.make_order()) #売買
        mk.on_market()
        World().next()

