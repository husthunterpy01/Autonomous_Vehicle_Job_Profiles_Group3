# Meeting in Group 3 - IT Capstone Project-20260727_053605-Meeting Recording

- **Date:** July 27, 2026, 5:36AM
- **Duration:** 38m 2s

> Martin Dang (24715379) started transcription

## Transcript

**Martin Dang (24715379) — 0:03**

Time to read a little bit about them, so you have a bit of an idea of what they're all about, but you will very quickly get an idea of what it's all about, and that's the goal for this project is you should become experts, yes, what's required to build autonomous vehicles. So, I don't know if I included in the job description thing, but there's this website here called AI Jobs.

So, and here, you know, people can just search for a job, you know, specifically, let's say data science or MLOps or whatever, in sort of anything, you know, the AI is a big field, so very, be a little bit more niche about what kind of jobs you'd like to find.

So ideally, we kind of want something similar to be built for our customer here. I did ask these people if they changed their website to also do autonomous vehicles, but they said no, because now the joke is with you. But what I'm more interested in is actually some of the data behind this website that drives it, because what I want to know is what are the

key technical skills and other kinds of aspects that people want. So I make sure that my new course actually teaches those tools, technologies and skills. Does that make sense? Yeah.

So what I have is basically a big list of, what is it, 42 different companies that make self-driving technology. So the idea is sort of we pick one at Brown, maybe Applied Intuition, because it's going to be in English.

So basically, when you go to each one of these companies, they always have like a career page or a join us. So when you click them, you know, you get an idea of what kinds of jobs they have. And then you can see, you know, they have lots of different kinds of jobs in different areas. Right. And so it's not good enough just to have saying, oh, there's jobs in autonomous equals because it

could be, hey, most of the things to do with reinforcement learning, for example. And so from my perspectives to my coursework, then there's no point in me teaching.

you know, I don't know, object tracking, whatever, if everybody's using reinforcement learning. So that's what it should be all about, if that makes sense. So the idea is each one of these websites, you'll be able to go there. I don't know how, I can't remember the name of it, but there is a scraper that almost all LLMs will use. It's up to you to use whatever technology you want, but

I personally think it's going to be easier if you just throw an LLM at the task. So the idea would be basically to scrape the websites to pull out, according to the job title, what kinds of skills and categories do we have. So it's really just a data extraction exercise to understand what.

what there is. And then again, it's up to you how you'd like to do it. I would probably just again throw it at an LLM and ask it all of these different kinds of jobs and descriptions. Can you cluster them into common profiles, right? So what does a hardware engineer do? And then you might say, okay, is that

If you have 3000 job ads in that one category, maybe you need to split it up into subcategories and say, okay, is there hardware sensing, hardware, compute, hardware, network, whatever? And you can either do that through your own brains and idle a little bit, but it'll also be using an LLM to try and classify, because at the end of the day, the idea is the website should just run.

Right, you shouldn't need to be manually filtering all these things. Yeah, and then from that, basically, what I would get is the ability to say, okay, everybody wants people who know how to do Gaussian slatting, so I need to teach everybody Gaussian slatting. So that's the thing that I'd be interested in. And Lee, your end customer, would say, okay, I want to know how many jobs.

I might, he might have skills in go since playing and say, well, how many jobs are out there that I can get in that field or whatever he happens to be interested in. That kind of makes sense that it's a bi-directional.

But that's the search for it, right, to just run through each of these and then provide a front end that is searchable, which again, I haven't really looked into it, but something similar to that would let you look through it. So I think one of the hard parts we'll be going through and figuring out how to scrape all of these different

websites, that will be a big challenge. I think there will be some challenge to how to develop your classifier, to classify all of those things automatically. And then there will be the usual challenge of building a front end that a customer likes and tells you no, it needs to be more pink or more blue, right?

It's fun conversations, but I think those would be the three main challenges.

So I've got a few more things to go through, but I'll just pause there to see if like general concept wise and again, architecture, it's up to you guys aim and build it, but to give you a bit of an idea, does that all kind of make sense so far? Is there anything?

Yeah, I know.

Okay, so what I would suggest you do is there are some open source self-driving systems out there. One of them is called AutoWare.

And most of these will have an open source like architecture diagram. So just some fun reading at night for you. I'd suggest you look through much of these diagrams because at the end of the day, a lot of the jobs are very technical and so they connect very closely to the architecture of the system, right? So

You know, you don't need to look into the details of these things unless you find it interesting and you want to. Hang on, it's a bit bigger.

So here, just as an example, right? So there will be jobs for people to do camera sensing. There's going to be jobs for people who do radar sensing and LiDAR sensing. So just by looking through all of these things, you can see what are the architectures and technologies that people use, and you will see that there will be jobs that...

relate to those topics. So it'll give you a bit of a structure to figure out what's the job profile and how does it cluster or how does it relate to an actual task in the system. So, you know, and then here, like this is the fusion thing. So again, you can see the different kinds of technologies that you use to merge and fuse different things together. So you'll see a bunch of jobs out there to do with.

fusion or object tracking, so if you start out here of what is kind of out there in terms of the job market, and then same thing here, start looking and say, okay, there's parking behaviours, there's land driving behaviours, there'll be people whose jobs correlate to these different technologies. So my advice is,

do some general reading because this is already pretty in depth, but do some general reading or, you know, I don't know if you've got a recommendation actually is like a good start introduction for pharmaceutical technology. But then the next, what I would do then after that, take another deep dive to look at some of these architecture diagrams so you understand how these systems fit together and what kinds of jobs.

Out there and how like it will fit together, if that kind of makes sense.

Do you have any suggestions, or like a really good basic introduction for Tom's vehicles? Is there something out there that just sort of is a sense of that? Well, I suggest it should be some of the data sets, and they might explain probably go to a bigger, biggest company like Waymorg.

Or even outweigh, they also introduce, they also have like a webpage where they can tell you what they want, what sort of purpose they want. So as well as also new skins, also the Altoverse. So there's a bunch of.

Like a different datasets and.

What was that again, an open source framework that actually looked? Yeah, that's a good idea. If you go through and look at some of these open sort of data sets, the good thing about these data sets is that it's visual. So when you look at these data sets, you get an idea of the kinds of technologies rather than looking at an architecture diagram which just says words.

You get a bit of an idea in pictures what the what the system does and kind of how it works.

Makes sense.

There's a question that you wanted to say. No, it's on here. Okay. Yeah, so yeah, those are the suggestions is to, I will send you some links, right? So have a look at some of the data sets, have a look at some of the architecture diagrams, but before we do that, just do some general Googling so that you get an idea.

And then to give you a concrete example, so this is a company that I used to work for. So you can see sort of the corporate, it was a smaller company, but you get an idea of the corporate structure and the kinds of jobs and how they sort of relate. So I think this area you kind of...

find a lot of information about, right? So these, when you just do some general Google and reading on autonomous systems, you'll know that they all have a map, they need to localize, they need to know where they are in the world, then to fuse a bunch of sensors, the lidars and cameras together, machine learning, usually a bit of a one.

I don't know how it is now, but back then that was a specialized team. You have usually a prediction team, so predicting what's going to happen in the future, so the car noise next. And you always have a motion planning or control algorithm sort of team. Again, we had a specialized team there on the GPU.

varies. But that's sort of that driving capability stuff that you'll get an idea on from some of those architecture diagrams. And then of course, for these autonomous vehicles, it's not just the onboard stuff, there's also off-board stuff. So you'll also find architecture diagrams on how the whole off-board and cloud infrastructure works. So yeah, that's where you'd see things like we call it the software platform. So

the build tools and build environment, the cloud infrastructure and the machine learning infrastructure that goes along with it, and then the vehicle platform is what was called in this company. So it would have to integrate your autonomous system into a car, right? So there's always that design element, so hardware engineers.

So it's the vehicle design and integration, in this case, operations as well. So there's usually test engineers and test drivers for all these cars. How to interface sensors, how to interface the vehicles controls, and how to set up all the embedded systems and computers and networks on the car itself.

And then, yeah, we had a separate V&V team. I think it's quite common, so you have a team that does the verification and validation, all the simulation systems, and all the visualization systems that go along with it. And then, yeah, you tend to have like a general process team, so software engineering processes.

code quality, that kind of stuff. In our testing team, scenarios teams, it's much bigger. So yeah, all the different test scenarios need to go through systems engineering kind of work, and then release management work. So this is really just the, yeah, like it says, kind of the engineering organization.

is what we're going to be focusing on, and depending on how they are, the different companies, like in this one, most of the test team is on a separate, but I would consider that part of the engineering process. But yeah, so that's kind of gives you an idea of what an actual company structure was of five years ago, whenever it was. So I think it looks different today. But the key thing is...

When you look at like an academic course on self-driving cars, they kind of focus on maybe these bits only, maybe a little bit of this. And as you can see, that is only a tiny part of what the entire picture of the engineering team looks like. So that's why I wanted this tool. So we can go through and find all the jobs and get an idea of what does this.

sort of picture look like? Where are most of the actual jobs over here on vehicle platforms or visualization? Very few people have jobs over here. I don't know what it looks like now. So that's kind of the idea.

Does that make sense? A little bit? I mean, I don't expect to understand all the technology behind it because you haven't had a chance to read up on it, but again, the general gist is I'm asking you guys to get familiar with different pieces of technology for autonomous vehicles and basically map it out to an org structure and we'll try and find some jobs online to figure out where does the demand in the industry

What kind of skill sets, right? So, I mean, as an example, right, like what you might find here, so something that you guys would have sort of seen a lot, like in your software processes. So, this could be things like, hey, you want people with skills, Git or Bazel or whatever, right? So, it's just gonna be what are the particular skills that are in demand for that kind of job.

Makes sense.

Cool.

Yeah, do, I mean, I just recommendations try. Well, what I was thinking approaching this is we've all approved some of the companies, so usually like Adrian do before he goes to one of the company and then see all of the shop visa.

So, what I think easily do is, like, maybe do a couple, one to two, maybe not three websites, and see what the keywords are actually about, like, for example, like, even to it was something like, but something like would be a bit.

Two details, so you want to do something more like a visions or maybe like that, or maybe sometimes like a processing or maybe sometimes it could be something like the C or CUDA engineering stuff like that, so you start off all of the list of keywords.

before you go and scrape all these companies. After you have all these keywords, then you go using LM to scrape those companies, like see whether these keywords apply to those websites, and then list out how many companies.

For onto this, it works and stuff like that, and then you can supply see the change from there based on the, yeah, so I think that's gonna be, and you also need to do database which afterward of what, so that you can show it into the.

the website, what not. Yeah, this is my, I think what should be a good approach, but feel free if you have any other better approach coming to this, but that's what I think would be the best for now. Yeah, yeah, I agree. So, I think.

Yeah, other look, so do a bunch of reading, become familiar with the field, have a look, like you said, for a bunch of different job profiles, so you get a bit of an idea of what kind of jobs and, you know, like the skill sets and things that they're asking for. It gives you a bit of a feel for it. Yeah, and then it'll be working your way through finding a

I think the key part of the job or key part of the work you're going to do, what's going to make your life easier is whichever scraping tool you use. If it does 99% of the work for you, it makes your job a lot easier than having to write your own specialized scraping tools. And then, yeah, like I said, I think the big thing then is to understand the data structure that you're trying to fill in. So try to...

maybe create an RL diagram for yourselves and say, okay, some things are pretty obvious, like there's a group within engineering, say, and in that group, there's a number of job role types, right? So some of those things are clear, and there'll be some skills that are specific to those role types, but yeah, some data structure you can use to.

to keep all that later together, because I think if you, again, it'll be up to you to figure this out, but I'm going to guess that if you just put a totally unstructured data into an ALM, it will collapse. So you probably need to do something else a bit.

Rag, like, and put the data, some kind of data structure.

Makes sense, yeah.

Yeah, I think, and then overall, at the end, the goal would be to make a website that is hosted somewhere. I wouldn't intend for it to be hosted at UWA, because I think that's too much of A challenge for the team, as far as I know. So I think you can just safely assume it'll just host it on whatever.

web service you like. I'll find something, got my credit card or whatever, website, domain name. So that's always the hardest part for me is figuring out what the domain name should be. And then yeah, in terms of LLMs and all that, I guess my assumption is because it's pretty small, like it's going to be text analysis.

You could probably, I would guess, get away with a pretty small model you can run locally. If you think you need big infrastructure, let me know, we can have a discussion about that too. But yeah, I would guess that Bitcoin.6 is going to run on your computer just fine for analyzing the clustering, but that'll be part of your journey to tell me if I'm right or wrong.

Right.

Yeah, cool. So I feel like kind of being bombarded with a whole bunch of information, but.

Does anyone of you want to have a go at being the parents and coming back to me with what you've understood and what we've heard and see if we've got a good understanding at this point between each other?

So, basically, what I understand from everything, yeah, you just need a website, yeah, from all the from the website, we just need some specific job titles, we can get the specific skills, yeah, we need to teach somebody any other course and bring the website if somebody wants to search a specific job or specific skills, we can easily search the.

On the website, yeah, yeah. So, basically, who is like, what is the like, who is the client? Is it the people finding the job, or is it just like the student who wants to like study what to do? So, I'm gonna use the data to figure out, like, what I want is an extractive.

So, you might come back to me and say, "You know what, everybody says you need to know Google, right? That's something that everybody needs to have. Every time a job, that's a common skill, which is, I'll use that for creating a course, but the end goal for the website that I think would be useful to have more people than just me. You can use that same data set to create a job searching website, right? So that...

Someone like Li can come here and say, "Hey, I want to be a I want to work with sensors, sensor fusion, and how many jobs are there for a sensor fusion engineer? So, you want to use the data for both of the companies?

So, for me, it's a one-off, so you can run like one-off script or something that just generates that information. Could be like, doesn't need to be reproducible anyway, but for the this this kind of customer job website should ideally you guys finish the website, you walk away and 10 years later.

It's still up and running and still working and telling us what, so the end goal is the website, the end goal, that's the end goal, but from a usable product perspective, the end goal is the website, OK, from a...

Generate data perspective, like the goal is, yeah, understand what to teach you. Does that make sense? Yeah.

And I must say, but in the job in the description on which we select the project, it was saying it's supposed to be a dashboard, but it is supposed to be a dashboard.

A dashboard? Yeah, so I understand this: I supposed to get a dashboard or the website. So, what I wanted from the dashboard is to see trends over time, right? Right, so basically seeing...

Um...

For example, let's see if it's okay, sorry, it's the wrong webpage, but let's go to this one. So, ideally, we would like to see over time saying, okay, there's less and less demand for people with GPU knowledge, for example, and increase the number of people who have envied and neural processing knowledge, right, so that we get a bit of a feel.

on those trends of which specific job roles are more or less popular over time. And then the other thing, which is just the total volume of jobs, for example, right? So say, hey, over time the industry is growing and there's more and more jobs or there's less and less jobs. So some basic statistics sort of.

So.

They are so visual, you also want the that should be part of the website. OK, the website, yeah, so you want like Jazz and everything be the part of the websites, the dashboard, yeah, yeah, OK, yeah, so just I'm not expecting that to be anything complicated. Again, like you can put yourself in the mindset.

So how do you got that? Two years. Okay, pretend it's a year or six months left, right? At that point in time, you've still got enough time to sort of, okay, I'm generally interested, but I don't know which specific role I'm going to target. So I might spend the next six months learning about AI so I can get the AI job run and spend the next six months learning how to program a GPU so I can get a GPU job run.

So the idea is to show them.

Imagine you were in the same position, right? Six months from now, you might graduate.

What are the skills that you should invest in, and are those skills trending upwards or downwards? That's that's. Yeah, to get the basic idea for the future jobs. Yeah, and is this market growing? Like, should I get into autonomous vehicles because there's more and more jobs every month, or is it less and less generally every month? It's everybody's specifically in ChatGPT once.

Yeah, you.

And, for the web-scapping part, like, if any list of from this, yes, like a specific list, you want to, yes, all of them or just few of them? No, so I would, so that can be an iterative discussion. What I'll do is give you that full list, because...

For me, the full list is good. It gives me a picture of the full industry, but I totally understand. Well, I would hope, actually, some of these probably have agreements with certain companies, like Libre or whatever it's called. Like, there's a bunch of these standard job ad companies. So maybe they already offer a standard API that you can just query.

and get the data from, or maybe they have them on LinkedIn and within you can query and get them from. So I'm expecting that some of these are going to be very easy to get. And then maybe other companies have all kinds of difficult things that feel close to stop people from spreading their website as they're going to be hard to get. So.

I hope they're all easy, but I'm very happy to say, here's the full list. You guys look at it and say, look, these five companies are impossible to get the scraping working on. Those ones are easy, but whatever, right? So, and as long as, like, there's only a few companies that are massive, right?

But most of these companies aren't that big. A lot of them are.

you know, less than a billion dollar kind of companies. On the other hand, there's a couple of, you know, 20 or 50 to $100 million companies. So if he came to me and said, I don't care what Google's got as a job, I propose it, don't scrape it. I say, no, try again, because they hire a lot of people running. So it'll be a negotiation.

Yeah, does that make sense?

And for the content that the content UI, is there any specific things you want or anything? It just has to be available or anything you want? OK.

Basically, basically, just something, yeah.

Yeah, so I guess, I mean, I would again, like kind of maybe base it on this one, with lack of it. I mean, you guys have a look around, but I mean, obvious things I would do is I'd be, yeah, I want to have a section of search for region, right? Am I looking for a job in Asia Pacific or am I looking for a job in America or whatever?

So, that's an obvious thing. The roles, like I said, is an obvious thing to search for, particular jobs. Yeah, might as well give them people an option to get down to specific countries and cities. I don't know. Experience level, I think, is a good one, because what I'd ask definitely is to have an internship option, because here at the university will be...

He was interns, but yet to have a different experience level. I don't care, but he's going to really care about summaries.

Have a search for that. I think those are probably the main things.

Salary wise, you might find that, I might know, not all companies just put on their job ads what the salaries are. So what you can do is just, best of what I found for technology stuff, have you guys used this, levels, FYM?

So if you just note that one down, this is a pretty good one, levels dot FYI, sort of crowdsourced information on jobs and salary levels. So yeah, if you're just trying to find salary information or estimate salary for a job.

Usually, with that, will say whether what you know, whether it's there'll be titles that correlate to the seniority of the job, like the level three, junior, mid, senior, principal, director, basically pretty much say. So, most of the those are some of the different level jobs will have a.

A salary you can get out of levels at my office, so you might have to do a separate.

To be honest, probably wouldn't even bother building a web scraper for that, just copy and paste the three salary levels across the spreadsheet or database of some description, but it's up to you guys. But if you're missing the salary information, you'll probably find it, but yeah, this website.

In other kids.

Alright, I think that, let's see here, let's see, I think it's missing difference.

Any other questions?

I would like to ask, how will you evaluate the right of the check? How will we evaluate whether the job classification is exact enough when there is some job have?

for example, the feature of engineer and other. Yeah, good question. I don't know. The answer is it's going to be a conversation. So some jobs you'll be able to easily quickly classify using your own opinion and whatever the LLM says, right? Other ones you'll say, hey, it's kind of borderline, and I think that's why we have a conversation between us and say, okay.

These funded jobs, we say it's this category or that category. So really, at the end of the day, we will effectively evolve a standard autonomous vehicle organization structure, right, between us and say, well, those are the kinds of roles we expect. Yeah, there's always going to be, because there's different sized companies.

Small companies will obviously have one job that suits multiple roles, right? So maybe we need to consider that in design.

With the larger companies, we have plenty of people to be very specific.

Yeah, all right. If you don't have any other questions, then I guess the suggestion was to talk through what we want to do, and then sort of first sort of go. So, as you can see, I think we've got a fairly...

good idea of what we sort of are asking for, but I think always good very early on in my opinion is to clarify the scope and the requirements. So if you go through a bit of a requirements solicitation where you have these sorts of discussions and you pull out you want to do we need to do X, Y and Z. I'm very happy personally, if this would be a two-way conversation, if you say, hey,

And I'm sure you're all looking for jobs as well, right? Okay, so you know what a job seeker needs. So if you say, hey, we've got to have this or that, I'm very happy to have, this is not a one way, it's going to be a collaborative effort to do this. So yeah, but I think that's important early on is that we agree on the scope and we do it through some requirements solicitations who say these are requirements.

And then also for each requirement, what is that acceptance criteria against it? So if there's a requirement to see salaries or what do we say? What I would like? Do I just, am I happy to range from one to million? No, because it's not information. I would know.

300,000 or whatever these sort of steps are, right? So we have some kind of what you've heard from us is a requirement and what you think is an acceptable answer to that requirement. Does that make sense? Yeah. So I think if we get those like clarified in the scope and the requirements early on, then hopefully it makes the whole sort of project.

Run smoother, and also I guess you've got a bit of time for it, but early on it's pretty good if we can also get an idea, because you have to, I guess you have some solutions you have to do at certain times, so to have an idea of what you must deliver at what time, and...

That way, we can make sure that when you're able to deliver whatever you need to deliver for the units, and we're not holding you back from, so a bit of a plan would be good to see. Yeah, and then, you know, I guess in this meeting, sort of give me an idea of the scope if you look into it and say, "Hey,

No way, we can't do X, Y, Z in the time we give it. Let's just have a conversation and either pull something out of scope or de-scope it or whatever. So doing something that's reasonable. But yeah, I think those are the first sort of things that I've been looking for. I don't know if there's anything particular you can do. No, that's useful.

On, we'll see when we get there, yeah, yeah, and then I think after that, probably the ER diagram to understand the data structure, and then...

I don't know how it is for you these days, but I'm under the impression that people can generate a GUI in like 3 seconds these days by asking ChatGP to do it, in which case I'll suggest we do like a rapid evaluation of different, like just generate a few different GUI designs because we should be able to do them very early on saying, yeah, that's what we want the user interface to actually look like.

And then you're in a pretty good position, because you have the you have the data input, you have the requirements, you know what the final GUI looks like, and then all you have to do is go and implement all the code, right? That's easy.

Period, but in my head, I'm sort of sketching out that way. Does that seem like a good approach to you guys? Yeah, and how have you decided to run your project? Are you going to Waterfall or Scrum, or what approach are you guys saying? I think it's supposed to be like Agile Swan. Agile Swan. OK, cool. So, every two weeks in the spring, yeah?

But then yeah, we can.

You figure it out, but probably around your scope, sprint planning meetings on time, basically wanna have a meeting and just catch up and make sure everything's coming good.

Seems like a good question then, if that would see, yeah.

Okay.

Um...

Nothing else. I don't know. I think I'm going to be a little bit mean and say I think I might be a little bit busier and harder to get hold of. So probably easier. So if it's OK with you, make you the first quarter call for any questions and then you can bounce them to me. Whatever else is that. I have more questions. So

Can we add you to a group chat so that we can update the, so you get a Teams channel product? Yeah, if you wanna add us both into your Teams channel, yeah.

Yeah, it works.

And, probably, yeah, I don't know what's best for you, but I'm not great at checking emails and stuff, probably team, probably teams, chat, chat is the best, yeah, yeah, also to keep in mind, don't spam too much, OK, yeah, sure, sure.

Ee.

Okay, so yeah, maybe one of if you guys want to get together and just put your notes together and then the things that I've promised to give you, make sure that you follow up with me. I'll try and send you an e-mail now with the things that I remember them, but then yeah, get back to me if there's anything missing. I'm just going to send through. Did you end up anything to this spiritually? I haven't got a chance, but I have a few on top.

I haven't been passing to, yeah, that's alright. We'll flick you up with what in this spreadsheet gives you a chance to click through.

Signage person, 10 companies to to browse through the websites, so you each get one of you. So, yeah, so I'll send you the list of the companies.

So I'll send you a list of the companies. I'll send that link to that AI job website, but at the end of any job websites, it's the same thing. The salary, I'll give you the links to levels FYI, send you a link to an architecture diagram, and some data sets.

But yeah, I think, sorry, I don't know of a good sort of.

Introduction to, or if you just go on YouTube and type in Introduction to Autonomous Vehicles, you'll probably find a good intro. Let's do it now.

So, like, very sad, because all the the upcoming, we should just be driving up in this thing. Yeah, there's like all sort of thinking. I'm looking, I was thinking it'd be like that, might not do that, might not do that.

Yeah.

I'd have to actually watch them to tell you they did, but yeah, but if you, if you Google Waymo chemos, there's a bunch of 20 minute videos, I'm sure, if you watch, yeah, you know, each person watches a different one, yeah, get together and say, "What did you learn? What did you say?" Yeah, yeah, someone will say, "I watched mine, it was terribly boring."

Someone else to say watch one is great, you can watch that one, yeah.

Tiew.

All good? Yeah.

Excited, so yes, it's gonna be, I mean, or two weeks' time, yeah, based on the sprint two weeks, whenever you get going with your sprint cycle, you can set up another meeting, but, like, I think in the meantime, just gonna...

Just click through emails or what, sorry, change channel, change channel for anything that I'm just saying touches.

And when is your first dinner? First year, 18th of the August. I see. OK, and what is it?

With association and your board, yeah, and group meetings, plans, stuff, project specs, and plans. OK, cool. So, that's exactly, yes, same, scope of work, requirements, project plan, and GUI design, right? Yeah.

People, that sounds like you got everything you need for the solution.

Yeah, yeah.

Cool.

Yeah, yeah.

Thank you. Everyone's happy. Yeah, so much. That's good. Okay, cool. Yeah, thanks for joining. Thanks for coming in. Looking forward to seeing an awesome website. There will be another group doing the same project. What my plan is to give everyone the same brief. The difference would just be in the terms of the data set. So

One group I give the self-driving cars on the road, another group the self-driving cars off the road. So basically what I tried to do.

Ohh.

No idea, but I assume that's all okay with the units and teams and want them, but in theory that means if there's another team you can talk to about which web scraping tool you're using on the routes.

We're running that school.

This one.

---

> Martin Dang (24715379) stopped transcription
