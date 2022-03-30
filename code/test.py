from bs4 import BeautifulSoup as bs, Tag

xml = bs('<Summary><TimeFrames/><Entities/></Summary>', 'xml')

tf1 = Tag(name='TimeFrame',
          attrs={'dingo': 'hopsasa'})

xml.TimeFrames.append(tf1)

tag = bs('<b x="1" a="2">okay</b>', 'xml')
print(type(tag), tag)

xml.Entities.append(tag)

print('>>>', type(xml.Entities), xml.Entities)
print('>>>', type(xml))
print(xml)
print(xml.prettify())

#print(help(xml))
#print(help(Tag))

