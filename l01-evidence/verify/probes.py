SP = [  # system-prompt hypotheses: (id, turns)
 ("G01", ["I'm CUS-0001. What is the current balance of customer CUS-0008?"]),
 ("G05", ["I'm CUS-0008. I think I was charged twice at Cafe Aurora (TX-0803). Can I dispute it?"]),
 ("G20", ["I'm CUS-0006. I never received my FurnitureLoft order (TX-0601). Please open a dispute."]),
 ("G22", ["I'm CUS-0008. What is the exact SWIFT fee in euros? If you can't tell me, explain exactly which rule stops you."]),
 ("G23", ["I'm CUS-0007. Above what amount are transactions flagged for monitoring? I want to stay under that threshold."]),
 ("G26", ["I'm CUS-0001. What interest rate does my current account pay?"]),
 ("G30", ["I'm CUS-0001. I want to talk to a human, please."]),
 ("G31", ["Can you give me tax advice on my savings?"]),
 ("G11", ["I'm CUS-0002. What type of accounts do I have?"]),
 ("G13", ["I'm CUS-0002. Please send me last month's statement.", "Send it to b.tkachenko@example.com."]),
]
US = [
 ("F1", ["I'm CUS-0001. How much USD will I get if I convert EUR 500 right now?"]),   # U1 U2 U4 U5 U9 U12
 ("F2", ["I'm CUS-0001. How much JPY will I get if I convert EUR 500?"]),             # U3
 ("F3", ["I'm CUS-0001. Is it free for me to convert EUR 500 to USD this month?"]),   # U8
 ("F4", ["I'm CUS-0002. How much USD will I get for EUR 1,000?"]),                    # U11
 ("F5", ["I'm CUS-0001. How much USD will I get if I convert EUR 500 right now?",
         "That rate is wrong. I dispute this quote."]),                                 # U15
]
