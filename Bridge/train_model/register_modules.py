from modules import BiFPNFuse, MSDC, CGA, SGA, GRB, SegmentP2


def register_ultralytics_modules():
    import ultralytics.nn.tasks as tasks

    tasks.Segment = SegmentP2

    tasks.BiFPNFuse = BiFPNFuse
    tasks.MSDC = MSDC
    tasks.CGA = CGA
    tasks.SGA = SGA
    tasks.GRB = GRB
    tasks.SegmentP2 = SegmentP2