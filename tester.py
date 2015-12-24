import requests
import json

url = 'http://localhost:12080/api/translate'

if __name__=="__main__":
    LOCALE = 'es'
    USERNAME = 'adam'
    params = {
        'amount': 5,
        'locale': LOCALE,
        'username': USERNAME
    }
    print 'getting'
    strings = requests.get(url,params).json()
    votes = []
    print strings
    for string in strings:
        print string
        print "<{id}>: '{original}'".format(**string)
        suggestions = string['suggestions']
        text = None
        if len(suggestions)>0:
            print "Select an existing suggestion:"
            for i,suggestion in enumerate(suggestions):
                print '{0}: {1}'.format(i,suggestion)
            print '999: None of the above'
            selection = raw_input('Your selection:')
            try:
                selection=int(selection)
                text = suggestions[selection]
            except:
                print "Nothing selected..."
        if text is None:
            text = raw_input('Your suggestion:')
        if text.strip()=='':
            continue
        votes.append({
            'locale'     :LOCALE,
            'resource_id':string['id'],
            'text'       :text
        })
    params = {
        'username': USERNAME,
        'votes': json.dumps(votes)
    }
    if len(strings) > 0:
        print 'putting'
        print requests.post(url,params).text
