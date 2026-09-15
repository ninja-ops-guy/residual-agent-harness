"""Invariant dependency graph for spec maintenance."""
INVARIANT_GRAPH={
 1:{"requires":(),"implies":(),"conflicts":()},
 2:{"requires":(),"implies":(3,),"conflicts":()},
 3:{"requires":(2,),"implies":(16,18),"conflicts":()},
 4:{"requires":(3,),"implies":(16,),"conflicts":()},
 5:{"requires":(),"implies":(13,),"conflicts":()},
 6:{"requires":(),"implies":(20,),"conflicts":()},
 7:{"requires":(),"implies":(15,),"conflicts":()},
 8:{"requires":(),"implies":(),"conflicts":()},
 9:{"requires":(),"implies":(19,),"conflicts":()},
 10:{"requires":(9,),"implies":(),"conflicts":()},
 11:{"requires":(7,),"implies":(),"conflicts":()},
 12:{"requires":(7,),"implies":(),"conflicts":()},
 13:{"requires":(3,5),"implies":(),"conflicts":()},
 14:{"