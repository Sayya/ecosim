from typing import List, Dict, Tuple
from enum import Enum, auto
from copy import copy # 浅いコピー
from abc import ABCMeta, abstractmethod # 抽象クラスを実現する
from random import gauss # 正規分布関数
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
        print("######## World Time: {0} ########".format(World.time))

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

# 一つの商品と数
class ItemSet: # amount >= 0を保証
    @type_check
    def __init__(self, name: Pd, amount: int):
        self.name = name
        self.item = ItemFactory().get(name) # FactoryからItem取得
        self.amount = amount

    def minus(self) -> 'ItemSet':
        return ItemSet(self.item.name, -self.amount)

# 商品と数のカタログ
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
        # 初日最初の獲得
        if self._count == 0:
            self._count += 1
            self.amount = amount
        # ２日目以降の獲得
        elif term > 0:
            self._count += 1
            # 次の予想獲得単位時間（平滑移動平均）
            self.forcast = ((self._count-1)*self.forcast + term)/self._count
            # 単位時間あたりのItemの獲得量（平滑移動平均）
            self.amount = ((self._count-1)*self.amount + (amount/term))/self._count
            self._time = World().time
        # 同日の場合
        elif self._count > 0:
            self.amount = ((self._count-1)*self.amount + amount)/self._count

# 製造のレシピ
class Recipe:
    @type_check
    def __init__(self, srcset: ItemCatalog, dstset: ItemCatalog):
        self.srcset = srcset.check_no_minus().clone()
        self.dstset = dstset.check_no_minus().clone()

    @type_check
    def manufact(self, properties: ItemCatalog) -> bool:
        try:
            properties.merge_no_minus(self.srcset.minus())
        except MinusError as e:
            print("{0}：製造できず".format(e))
            return False
        properties.merge(self.dstset)
        return True

# 消費の間隔
class Schedule:
    @type_check
    def __init__(self, duration: int):
        self.duration = duration
        self.start = World.time
    
    def update(self):
        if World().time >= self.start + self.duration:
            self.start = World().time
            return True
        else:
            return False

# 生産性の管理
class Progress:
    @type_check
    def __init__(self, mu: float, sigma: float):
        self.mu = mu
        self.sigma = sigma
        self.tank = 0
    
    def update(self):
        self.tank += gauss(self.mu, self.sigma)
        if self.tank >= 1:
            self.tank %= 1
            return True
        else:
            return False

class Agent:
    @type_check
    def __init__(self, name: str, products: ItemCatalog, nessesities: ItemCatalog,
                properties: ItemCatalog, schedule: Schedule, progress: Progress):
        self.name = name
        self.products = products.check_no_minus().clone() # 単位時間に生産できるItemセット
        self.nessesities = nessesities.check_no_minus().clone() # World.time単位につき必要なItemセット
        self.properties = properties.check_no_minus().clone() # 所有Item初期設定
        self.schedule = copy(schedule)
        self.progress = copy(progress)
        # Dict[Item,Expect]
        self.expects = {k: Expect() for k in nessesities.keys()}

    def produce(self):
        if self.progress.update():
            self.properties.merge(self.products)
            print("{0}は生産".format(self.name))

    def consume(self):
        if self.schedule.update():
            # 必要分を所有から差し引き
            self.properties.merge(self.nessesities.minus())
            print("{0}は消費".format(self.name))

    @type_check
    def accept(self, diff: ItemSet):
        self.properties.add(diff)
        if diff.item in self.expects.keys():
            self.expects[diff.item].estimate(diff.amount)

    @type_check
    def pay(self, diff: ItemSet):
        self.properties.add_no_minus(diff.minus())

    @type_check
    def manufact(self, recipe: Recipe):
        return recipe.manufact(self.properties)

    @type_check
    def manufact_all(self, recipe: Recipe):
        while self.manufact(recipe):
            print("{0}は製造".format(self.name))

    def make_order(self) -> 'Order':
        # 消費発動後の所有Item
        future_assets = self.nessesities.minus().merge(self.properties)
        # 不足分を欲しい物セットに
        buysets = ItemCatalog([ItemSet(k.name, -v) for k, v in future_assets.items() if v < 0])
        # 残り分を売り物セットに
        selsets = ItemCatalog([ItemSet(k.name, v) for k, v in future_assets.items() if v > 0])
        return Order(self, buysets, selsets)

class Order:
    @type_check
    def __init__(self, agent: Agent, buy_goods: ItemCatalog, sel_goods: ItemCatalog):
        self.agent = agent
        self.buy_goods = buy_goods.check_no_minus()
        self.sel_goods = sel_goods.check_no_minus()

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
        self.agents = list()

    @type_check
    def add_agent(self, agent: Agent):
        self.agents.append(agent)

    def on_market(self):
        # 買い物客が
        for buyer in self.agents:
            # いろんな店舗に出向き
            for seller in self.agents:
                # もちろん自分の店舗以外で
                if buyer is not seller:
                    # 欲しい物がないか探す
                    wants = buyer.make_order().buy_goods
                    for want, amount in wants.items():
                        # もし欲しい物があったら
                        goods = seller.make_order().sel_goods
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
                            try:
                                buyer.pay(price) # 買い手側のみ料金の不足がありうる
                                seller.pay(bought)
                                buyer.accept(bought)
                                seller.accept(price)
                                print("{0}が{1}から{2}[{3}]を{4}[{5}]で購入".format(
                                        buyer.name, seller.name, 
                                        bought.name, bought.amount, 
                                        price.name, price.amount
                                    ))
                            except MinusError as e:
                                print("{0}：{1}が{2}[{3}]を購入できず".format(
                                        e, buyer.name, bought.name, bought.amount
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

class MinusMergeError(MinusError):
    pass

class NoUnitError(Error):
    pass

class NoPriceError(Error):
    pass

if __name__ == '__main__':
    # 商品と数の定義
    lavor1  = ItemSet(Pd.LAVOR, 1)
    lavor30  = ItemSet(Pd.LAVOR, 30)
    money1  = ItemSet(Pd.MONEY, 1)
    money3  = ItemSet(Pd.MONEY, 3)
    meal1  = ItemSet(Pd.MEAL, 1)
    money100 = ItemSet(Pd.MONEY, 100)
    none0   = ItemSet(Pd.NONE, 0)

    # 商品と数のカタログの定義
    lavor1_c  = ItemCatalog([lavor1])
    lavor30_c  = ItemCatalog([lavor30])
    money1_c  = ItemCatalog([money1])
    money3_c  = ItemCatalog([money3])
    meal1_c  = ItemCatalog([meal1])
    money100_c = ItemCatalog([money100])
    none0_c   = ItemCatalog([none0])

    # 製造のレシピ
    rc1 = Recipe(lavor1_c, meal1_c)

    # 消費の間隔
    sch1 = Schedule(1)
    sch30 = Schedule(30)
    sch0 = Schedule(0)

    # 生産性の管理
    pgr1 = Progress(1.0, 0.2) # ブレのある平均的生産性
    pgr2 = Progress(1.1, 0.1) # 安定した高生産性
    pgr3 = Progress(0.8, 0.5) # 不安定な低生産性
    pgr0 = Progress(0.0, 0.0)

    agents = list()
    agents.append(Agent("A1", lavor1_c, meal1_c, money3_c, sch1, pgr1))
    agents.append(Agent("A2", lavor1_c, meal1_c, money3_c, sch1, pgr2))
    agents.append(Agent("A3", lavor1_c, meal1_c, money3_c, sch1, pgr3))
    plant = Agent("Plant", none0_c, lavor30_c, money100_c, sch0, pgr0)

    mk = Market([Price(lavor1, money1), Price(meal1, money1)])

    for agent in agents:
        mk.add_agent(agent) #売買
    mk.add_agent(plant) #売買

    while True:
        for agent in agents:
            agent.produce() #生産
            agent.consume() #消費
        plant.manufact_all(rc1) #製造（変換）
        mk.on_market()
        World().next()

